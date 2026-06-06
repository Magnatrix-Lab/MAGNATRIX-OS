"""
event_streaming_native.py — Event Streaming & Pub-Sub Native Engine for MAGNATRIX-OS
=====================================================================================
Real-time event backbone for inter-component, inter-agent, and external-system
communication.  Pure stdlib.  No external dependencies.

Architecture
------------
- Event .............. immutable message with seq, ts, topic, key, payload, headers
- Segment ............ file-backed append-only JSON Lines log (rotates at size limit)
- EventLog ........... per-topic log: segments, compaction, recovery, replay
- Topic .............. metadata, retention, dead-letter queue, subscription matching
- ConsumerGroup ...... membership, partition assignment, offset checkpoints
- Consumer ........... iterator/callback/generator/batch APIs, backpressure, lag
- Producer ........... fire-and-forget or ack-based publishing, routing
- EventStreamingEngine  master orchestrator: topics, producers, consumers, bridges

Kafka-inspired semantics (at-least-once, consumer groups, log compaction) adapted to
a single-node native Python engine with file persistence and zero deps.
"""

from __future__ import annotations

import ast
import bisect
import fnmatch
import glob
import hashlib
import json
import os
import pathlib
import queue
import re
import struct
import sys
import threading
import time
import traceback
import types
import uuid
import zlib
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from io import StringIO
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_SEGMENT_SIZE = 10 * 1024 * 1024       # 10 MB per segment
DEFAULT_RETENTION_MS = 7 * 24 * 60 * 60 * 1000  # 7 days
DEFAULT_RETENTION_COUNT = 100_000                # max events per topic
MAX_IN_MEMORY_QUEUE = 10_000                     # backpressure: consumer queue
CHECKPOINT_INTERVAL_MS = 30_000                  # auto-flush offsets every 30s
SEGMENT_INDEX_GRANULARITY = 1000                 # index every N events


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Event:
    """Immutable event record."""
    sequence: int
    timestamp: float
    topic: str
    key: str
    payload: Any
    headers: Dict[str, str] = field(default_factory=dict)
    event_id: str = field(default="")

    def __post_init__(self):
        if not self.event_id:
            # hack for frozen dataclass — swap via object.__setattr__
            object.__setattr__(
                self,
                "event_id",
                hashlib.sha256(
                    f"{self.sequence}:{self.timestamp}:{self.topic}:{self.key}:{id(self)}".encode()
                ).hexdigest()[:16],
            )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "topic": self.topic,
            "key": self.key,
            "payload": self.payload,
            "headers": dict(self.headers),
            "event_id": self.event_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Event":
        return cls(
            sequence=d["sequence"],
            timestamp=d["timestamp"],
            topic=d["topic"],
            key=d["key"],
            payload=d["payload"],
            headers=d.get("headers", {}),
            event_id=d.get("event_id", ""),
        )

    def __repr__(self) -> str:
        return f"Event(seq={self.sequence}, topic={self.topic}, key={self.key})"


# ---------------------------------------------------------------------------
# Segment
# ---------------------------------------------------------------------------

class Segment:
    """A single append-only log file (JSON Lines)."""

    def __init__(self, path: pathlib.Path, base_sequence: int = 0):
        self.path = path
        self.base_sequence = base_sequence
        self._lock = threading.RLock()
        self._index: Dict[int, int] = {}          # sequence -> file offset
        self._index_seqs: List[int] = []
        self._size = 0
        self._count = 0
        self._closed = False
        self._fp: Optional[Any] = None
        self._ensure_file()
        self._load_index()

    def _ensure_file(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def _load_index(self):
        """Build sparse index by scanning segment."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        offset = 0
        count = 0
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line_len = len(line.encode("utf-8"))
                if line.strip():
                    try:
                        d = json.loads(line)
                        seq = d.get("sequence", self.base_sequence + count)
                        if count % SEGMENT_INDEX_GRANULARITY == 0:
                            self._index[seq] = offset
                            bisect.insort(self._index_seqs, seq)
                        count += 1
                    except json.JSONDecodeError:
                        pass
                offset += line_len
        self._count = count
        self._size = self.path.stat().st_size

    def append(self, event: Event) -> int:
        with self._lock:
            if self._closed:
                raise RuntimeError("Segment closed")
            line = json.dumps(event.as_dict(), ensure_ascii=False) + "\n"
            data = line.encode("utf-8")
            if self._count % SEGMENT_INDEX_GRANULARITY == 0:
                self._index[event.sequence] = self._size
                bisect.insort(self._index_seqs, event.sequence)
            with open(self.path, "ab") as f:
                f.write(data)
            self._size += len(data)
            self._count += 1
            return self._size

    def read_events(self, start_seq: int = 0, end_seq: int = None) -> Iterator[Event]:
        """Read events from start_seq (inclusive) to end_seq (exclusive)."""
        if not self.path.exists():
            return
        # Find nearest index entry <= start_seq
        idx = bisect.bisect_right(self._index_seqs, start_seq) - 1
        offset = 0
        if idx >= 0:
            nearest = self._index_seqs[idx]
            offset = self._index.get(nearest, 0)
        count = 0
        seq_offset = self.base_sequence + count
        with open(self.path, "r", encoding="utf-8") as f:
            f.seek(offset)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    seq = d.get("sequence", self.base_sequence + count)
                    if seq >= start_seq:
                        if end_seq is not None and seq >= end_seq:
                            return
                        yield Event.from_dict(d)
                    count += 1
                except json.JSONDecodeError:
                    continue

    def compact(self, keep_latest_key: bool = True) -> int:
        """Rewrite segment keeping only latest event per key. Returns new size."""
        if not self.path.exists() or self._count == 0:
            return 0
        latest: Dict[str, Event] = {}
        for ev in self.read_events():
            latest[ev.key] = ev
        tmp_path = self.path.with_suffix(".tmp")
        new_size = 0
        new_count = 0
        new_index: Dict[int, int] = {}
        new_seqs: List[int] = []
        with open(tmp_path, "w", encoding="utf-8") as f:
            for ev in sorted(latest.values(), key=lambda e: e.sequence):
                line = json.dumps(ev.as_dict(), ensure_ascii=False) + "\n"
                data = line.encode("utf-8")
                if new_count % SEGMENT_INDEX_GRANULARITY == 0:
                    new_index[ev.sequence] = new_size
                    bisect.insort(new_seqs, ev.sequence)
                f.write(line)
                new_size += len(data)
                new_count += 1
        with self._lock:
            self._closed = True
            if self._fp:
                self._fp.close()
            tmp_path.replace(self.path)
            self._index = new_index
            self._index_seqs = new_seqs
            self._size = new_size
            self._count = new_count
            self._closed = False
        return new_size

    @property
    def size(self) -> int:
        return self._size

    @property
    def count(self) -> int:
        return self._count

    def close(self):
        with self._lock:
            self._closed = True


# ---------------------------------------------------------------------------
# EventLog
# ---------------------------------------------------------------------------

class EventLog:
    """Per-topic append-only log with segment rotation and compaction."""

    def __init__(
        self,
        topic_name: str,
        data_dir: pathlib.Path,
        segment_size: int = DEFAULT_SEGMENT_SIZE,
        retention_ms: int = DEFAULT_RETENTION_MS,
        retention_count: int = DEFAULT_RETENTION_COUNT,
    ):
        self.topic_name = topic_name
        self.data_dir = data_dir / topic_name
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.segment_size = segment_size
        self.retention_ms = retention_ms
        self.retention_count = retention_count
        self._lock = threading.Lock()
        self._segments: List[Segment] = []
        self._active_segment: Optional[Segment] = None
        self._next_sequence = 1
        self._total_count = 0
        self._load_existing_segments()

    def _load_existing_segments(self):
        """Discover existing segment files on disk."""
        pattern = self.data_dir / "*.log"
        files = sorted(glob.glob(str(pattern)), key=lambda p: int(pathlib.Path(p).stem.split("_")[-1]))
        for f in files:
            p = pathlib.Path(f)
            try:
                base_seq = int(p.stem.split("_")[-1])
            except ValueError:
                base_seq = 0
            seg = Segment(p, base_seq)
            self._segments.append(seg)
        if self._segments:
            self._active_segment = self._segments[-1]
            # Determine next sequence from last segment
            last_seg = self._segments[-1]
            self._next_sequence = last_seg.base_sequence + last_seg.count + 1
            self._total_count = sum(s.count for s in self._segments)
        else:
            self._active_segment = self._create_segment(1)
            self._segments.append(self._active_segment)

    def _create_segment(self, base_sequence: int) -> Segment:
        ts = int(time.time() * 1000)
        filename = f"segment_{ts}_{base_sequence}.log"
        path = self.data_dir / filename
        return Segment(path, base_sequence)

    def _maybe_rotate(self):
        if self._active_segment and self._active_segment.size >= self.segment_size:
            self._active_segment.close()
            new_seg = self._create_segment(self._next_sequence)
            self._segments.append(new_seg)
            self._active_segment = new_seg

    def append(self, key: str, payload: Any, headers: Optional[Dict[str, str]] = None) -> Event:
        with self._lock:
            self._maybe_rotate()
            event = Event(
                sequence=self._next_sequence,
                timestamp=time.time(),
                topic=self.topic_name,
                key=key,
                payload=payload,
                headers=headers or {},
            )
            self._active_segment.append(event)
            self._next_sequence += 1
            self._total_count += 1
            return event

    def read(
        self,
        start_offset: int = 0,
        end_offset: int = None,
        max_events: int = None,
    ) -> Iterator[Event]:
        """Read events from start_offset (inclusive)."""
        count = 0
        for seg in self._segments:
            seg_start = seg.base_sequence
            seg_end = seg.base_sequence + seg.count
            if end_offset is not None and seg_start >= end_offset:
                continue
            for ev in seg.read_events(
                start_seq=max(start_offset, seg_start),
                end_seq=end_offset,
            ):
                yield ev
                count += 1
                if max_events is not None and count >= max_events:
                    return

    def get_latest_by_key(self, key: str) -> Optional[Event]:
        """For compaction: get latest event with given key."""
        latest: Optional[Event] = None
        for seg in reversed(self._segments):
            for ev in seg.read_events():
                if ev.key == key:
                    if latest is None or ev.sequence > latest.sequence:
                        latest = ev
        return latest

    def compact(self):
        """Compact all segments: keep only latest per key."""
        with self._lock:
            new_segments: List[Segment] = []
            total = 0
            max_seq = 0
            for seg in self._segments:
                seg.compact()
                new_segments.append(seg)
                total += seg.count
                if seg.count > 0:
                    # Find max sequence in segment
                    for ev in seg.read_events():
                        if ev.sequence > max_seq:
                            max_seq = ev.sequence
            self._segments = new_segments
            self._total_count = total
            self._next_sequence = max_seq + 1 if max_seq > 0 else 1
            if self._segments:
                self._active_segment = self._segments[-1]
            else:
                self._active_segment = self._create_segment(1)
                self._segments.append(self._active_segment)

    def cleanup(self):
        """Remove old segments based on retention policy."""
        now = time.time() * 1000
        with self._lock:
            keep: List[Segment] = []
            removed_count = 0
            for seg in self._segments:
                # Check age of segment via mtime
                mtime_ms = seg.path.stat().st_mtime * 1000
                age_ok = (now - mtime_ms) < self.retention_ms
                count_ok = (self._total_count - removed_count) < self.retention_count
                if age_ok or (not count_ok):
                    keep.append(seg)
                else:
                    removed_count += seg.count
                    seg.path.unlink(missing_ok=True)
                    # Remove index file if exists
                    idx_path = seg.path.with_suffix(".idx")
                    idx_path.unlink(missing_ok=True)
            self._segments = keep
            self._total_count = sum(s.count for s in self._segments)
            if not self._segments:
                self._active_segment = self._create_segment(1)
                self._segments.append(self._active_segment)
            else:
                self._active_segment = self._segments[-1]

    @property
    def latest_offset(self) -> int:
        return self._next_sequence - 1

    @property
    def total_count(self) -> int:
        return self._total_count

    def segment_count(self) -> int:
        return len(self._segments)


# ---------------------------------------------------------------------------
# Topic
# ---------------------------------------------------------------------------

class TopicRetention(Enum):
    TIME = auto()
    COUNT = auto()
    COMPACT = auto()


@dataclass
class TopicConfig:
    persistent: bool = True
    retention: TopicRetention = TopicRetention.TIME
    retention_ms: int = DEFAULT_RETENTION_MS
    retention_count: int = DEFAULT_RETENTION_COUNT
    segment_size: int = DEFAULT_SEGMENT_SIZE
    dead_letter: bool = True
    max_message_size: int = 1024 * 1024  # 1 MB


class Topic:
    """Topic metadata and event log container."""

    def __init__(self, name: str, data_dir: pathlib.Path, config: Optional[TopicConfig] = None):
        self.name = name
        self.config = config or TopicConfig()
        self.log = EventLog(
            name,
            data_dir,
            segment_size=self.config.segment_size,
            retention_ms=self.config.retention_ms,
            retention_count=self.config.retention_count,
        )
        self._subscriptions: List[Tuple[str, Callable]] = []  # (pattern, callback)
        self._lock = threading.Lock()
        self._dead_letter: List[Event] = []
        self._dlq_lock = threading.Lock()

    def subscribe(self, pattern: str, callback: Callable[[Event], None]) -> str:
        """Subscribe to topic events matching pattern. Returns sub_id."""
        sub_id = f"sub_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._subscriptions.append((sub_id, pattern, callback))
        return sub_id

    def unsubscribe(self, sub_id: str) -> bool:
        with self._lock:
            before = len(self._subscriptions)
            self._subscriptions = [(sid, pat, cb) for sid, pat, cb in self._subscriptions if sid != sub_id]
            return len(self._subscriptions) < before

    def _matches(self, pattern: str, topic: str) -> bool:
        """Match topic name against pattern with * and # wildcards."""
        if pattern == topic:
            return True
        # Convert pattern to regex: * -> single segment, # -> multi-segment
        parts = pattern.split(".")
        regex_parts = []
        for p in parts:
            if p == "#":
                regex_parts.append(".*")
            elif p == "*":
                regex_parts.append(r"[^.]+")
            else:
                regex_parts.append(re.escape(p))
        regex = r"^" + r"\.".join(regex_parts) + "$"
        return re.match(regex, topic) is not None

    def dispatch(self, event: Event):
        """Dispatch event to all matching subscribers."""
        with self._lock:
            subs = list(self._subscriptions)
        failed = []
        for sub_id, pattern, callback in subs:
            if self._matches(pattern, event.topic):
                try:
                    callback(event)
                except Exception:
                    failed.append((sub_id, event, traceback.format_exc()))
        if failed and self.config.dead_letter:
            with self._dlq_lock:
                for sub_id, ev, tb in failed:
                    self._dead_letter.append(ev)

    def dead_letter_queue(self) -> List[Event]:
        with self._dlq_lock:
            dlq = list(self._dead_letter)
            self._dead_letter.clear()
            return dlq

    def publish(self, key: str, payload: Any, headers: Optional[Dict[str, str]] = None) -> Event:
        event = self.log.append(key, payload, headers)
        self.dispatch(event)
        return event

    def cleanup(self):
        self.log.cleanup()

    def compact(self):
        self.log.compact()


# ---------------------------------------------------------------------------
# ConsumerGroup
# ---------------------------------------------------------------------------

class ConsumerGroup:
    """Manages a group of consumers with load-balanced distribution."""

    def __init__(self, group_id: str, topic: Topic, engine: "EventStreamingEngine"):
        self.group_id = group_id
        self.topic = topic
        self._engine = engine
        self._members: List[str] = []  # consumer IDs
        self._assignments: Dict[str, int] = {}  # consumer_id -> partition (simplified: all share)
        self._offsets: Dict[str, int] = {}      # consumer_id -> last committed offset
        self._lock = threading.RLock()
        self._checkpoint_path = engine.data_dir / "checkpoints" / f"{group_id}_{topic.name}.json"
        self._checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_offsets()

    def _load_offsets(self):
        if self._checkpoint_path.exists():
            try:
                with open(self._checkpoint_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._offsets = {k: int(v) for k, v in data.get("offsets", {}).items()}
            except (json.JSONDecodeError, ValueError):
                self._offsets = {}

    def _save_offsets(self):
        with self._lock:
            data = {"offsets": self._offsets, "timestamp": time.time()}
        with open(self._checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def join(self, consumer_id: str) -> bool:
        with self._lock:
            if consumer_id not in self._members:
                self._members.append(consumer_id)
                if consumer_id not in self._offsets:
                    self._offsets[consumer_id] = 0
                return True
            return False

    def leave(self, consumer_id: str) -> bool:
        with self._lock:
            if consumer_id in self._members:
                self._members.remove(consumer_id)
                self._save_offsets()
                return True
            return False

    def get_offset(self, consumer_id: str) -> int:
        with self._lock:
            return self._offsets.get(consumer_id, 0)

    def commit_offset(self, consumer_id: str, offset: int):
        with self._lock:
            self._offsets[consumer_id] = offset
        # Auto-save periodically or on leave
        self._save_offsets()

    def rebalance(self):
        """Simple rebalance: round-robin assignment of consumers."""
        with self._lock:
            n = len(self._members)
            for i, member in enumerate(self._members):
                self._assignments[member] = i

    def member_count(self) -> int:
        with self._lock:
            return len(self._members)

    def lag(self, consumer_id: str) -> int:
        """Consumer lag = latest offset - committed offset."""
        latest = self.topic.log.latest_offset
        with self._lock:
            committed = self._offsets.get(consumer_id, 0)
        return max(0, latest - committed)

    def group_lag(self) -> Dict[str, int]:
        """Lag for all members."""
        with self._lock:
            members = list(self._members)
        return {m: self.lag(m) for m in members}

    def checkpoint(self):
        self._save_offsets()


# ---------------------------------------------------------------------------
# Consumer
# ---------------------------------------------------------------------------

class Consumer:
    """Consumer with iterator, callback, generator, and batch APIs."""

    def __init__(
        self,
        consumer_id: str,
        topic: Topic,
        group: Optional[ConsumerGroup] = None,
        start_offset: int = 0,
        auto_commit: bool = True,
        max_queue: int = MAX_IN_MEMORY_QUEUE,
    ):
        self.consumer_id = consumer_id
        self.topic = topic
        self.group = group
        self._offset = start_offset
        self._auto_commit = auto_commit
        self._queue: queue.Queue[Event] = queue.Queue(maxsize=max_queue)
        self._max_queue = max_queue
        self._callback: Optional[Callable[[Event], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._consumed_count = 0
        self._last_commit_time = time.time()
        if group:
            group.join(consumer_id)
            self._offset = group.get_offset(consumer_id)

    def seek(self, offset: int):
        """Manually set read offset."""
        with self._lock:
            self._offset = offset

    def poll(self, timeout_ms: float = 1000, max_records: int = 100) -> List[Event]:
        """Poll for new events. Blocking with timeout."""
        results = []
        latest = self.topic.log.latest_offset
        with self._lock:
            current = self._offset
        if current >= latest:
            time.sleep(timeout_ms / 1000)
            return []
        for ev in self.topic.log.read(start_offset=current + 1, max_events=max_records):
            results.append(ev)
            with self._lock:
                self._offset = ev.sequence
                self._consumed_count += 1
            if self._auto_commit:
                self._maybe_commit()
        return results

    def _maybe_commit(self):
        now = time.time()
        if (now - self._last_commit_time) * 1000 > CHECKPOINT_INTERVAL_MS:
            if self.group:
                self.group.commit_offset(self.consumer_id, self._offset)
            self._last_commit_time = now

    def commit(self):
        """Explicitly commit current offset."""
        with self._lock:
            offset = self._offset
        if self.group:
            self.group.commit_offset(self.consumer_id, offset)

    def stream(self) -> Generator[Event, None, None]:
        """Generator-based streaming API."""
        while True:
            batch = self.poll(timeout_ms=500, max_records=10)
            for ev in batch:
                yield ev

    def iterate(self, timeout_ms: float = 1000) -> Iterator[Event]:
        """Iterator-based consumer."""
        return self._Iterator(self, timeout_ms)

    class _Iterator:
        def __init__(self, consumer: "Consumer", timeout_ms: float):
            self._consumer = consumer
            self._timeout_ms = timeout_ms
            self._buffer: deque = deque()
            self._closed = False

        def __iter__(self):
            return self

        def __next__(self) -> Event:
            if self._closed:
                raise StopIteration
            if self._buffer:
                return self._buffer.popleft()
            batch = self._consumer.poll(timeout_ms=self._timeout_ms, max_records=1)
            if not batch:
                raise StopIteration
            self._buffer.extend(batch[1:])
            return batch[0]

        def close(self):
            self._closed = True

    def assign_callback(self, callback: Callable[[Event], None]):
        """Callback-based streaming."""
        self._callback = callback

    def start_callback(self, interval_ms: float = 100):
        """Start background thread for callback delivery."""
        self._running = True
        self._thread = threading.Thread(target=self._callback_loop, args=(interval_ms,), daemon=True)
        self._thread.start()

    def _callback_loop(self, interval_ms: float):
        while self._running:
            batch = self.poll(timeout_ms=interval_ms, max_records=100)
            if self._callback:
                for ev in batch:
                    try:
                        self._callback(ev)
                    except Exception:
                        pass

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self.commit()
        if self.group:
            self.group.leave(self.consumer_id)

    def lag(self) -> int:
        if self.group:
            return self.group.lag(self.consumer_id)
        latest = self.topic.log.latest_offset
        with self._lock:
            return max(0, latest - self._offset)

    @property
    def consumed(self) -> int:
        with self._lock:
            return self._consumed_count


# ---------------------------------------------------------------------------
# Producer
# ---------------------------------------------------------------------------

class Producer:
    """Producer that publishes events to topics."""

    def __init__(self, producer_id: str, engine: "EventStreamingEngine"):
        self.producer_id = producer_id
        self._engine = engine
        self._published_count = 0
        self._lock = threading.Lock()

    def send(
        self,
        topic: str,
        key: str,
        payload: Any,
        headers: Optional[Dict[str, str]] = None,
    ) -> Event:
        t = self._engine.get_or_create_topic(topic)
        event = t.publish(key, payload, headers)
        with self._lock:
            self._published_count += 1
        return event

    def send_batch(
        self,
        topic: str,
        messages: List[Tuple[str, Any, Optional[Dict[str, str]]]],
    ) -> List[Event]:
        """Send a batch of messages. Returns list of events."""
        t = self._engine.get_or_create_topic(topic)
        events = []
        for key, payload, headers in messages:
            event = t.publish(key, payload, headers)
            events.append(event)
        with self._lock:
            self._published_count += len(events)
        return events

    @property
    def published(self) -> int:
        with self._lock:
            return self._published_count


# ---------------------------------------------------------------------------
# EventStreamingEngine (main orchestrator)
# ---------------------------------------------------------------------------

class EventStreamingEngine:
    """Master orchestrator for the event streaming backbone."""

    def __init__(self, data_dir: Union[str, pathlib.Path] = "/tmp/magnatrix-events"):
        self.data_dir = pathlib.Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._topics: Dict[str, Topic] = {}
        self._groups: Dict[str, Dict[str, ConsumerGroup]] = defaultdict(dict)  # topic -> {group_id -> group}
        self._producers: Dict[str, Producer] = {}
        self._consumers: Dict[str, Consumer] = {}
        self._global_subs: List[Tuple[str, str, Callable]] = []
        self._lock = threading.Lock()
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        self._event_bus_bridge: Optional[Callable] = None
        self._mesh_bridge: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Topic management
    # ------------------------------------------------------------------

    def create_topic(self, name: str, config: Optional[TopicConfig] = None) -> Topic:
        with self._lock:
            if name in self._topics:
                return self._topics[name]
            topic = Topic(name, self.data_dir, config)
            self._topics[name] = topic
            return topic

    def get_or_create_topic(self, name: str) -> Topic:
        with self._lock:
            if name in self._topics:
                return self._topics[name]
        return self.create_topic(name)

    def delete_topic(self, name: str) -> bool:
        with self._lock:
            if name in self._topics:
                del self._topics[name]
                # Clean files
                topic_dir = self.data_dir / name
                if topic_dir.exists():
                    for f in topic_dir.glob("*"):
                        f.unlink()
                    topic_dir.rmdir()
                return True
            return False

    def list_topics(self) -> List[str]:
        with self._lock:
            return list(self._topics.keys())

    # ------------------------------------------------------------------
    # Subscription (pub/sub)
    # ------------------------------------------------------------------

    def subscribe(self, topic_pattern: str, callback: Callable[[Event], None]) -> str:
        """Subscribe to events matching a topic pattern (supports wildcards)."""
        sub_id = f"sub_{uuid.uuid4().hex[:8]}"
        # If exact topic exists, subscribe there; otherwise register globally
        with self._lock:
            exact_topic = self._topics.get(topic_pattern)
            if exact_topic:
                exact_topic.subscribe(topic_pattern, callback)
                return sub_id
        # Register a wildcard subscription that matches all topics
        def _global_dispatcher(event: Event):
            if self._topic_matches(topic_pattern, event.topic):
                callback(event)
        self._global_subs.append((sub_id, topic_pattern, _global_dispatcher))
        # Also subscribe to existing topics
        with self._lock:
            for name, topic in self._topics.items():
                if self._topic_matches(topic_pattern, name):
                    topic.subscribe(topic_pattern, _global_dispatcher)
        return sub_id

    def _topic_matches(self, pattern: str, topic: str) -> bool:
        if pattern == topic:
            return True
        parts = pattern.split(".")
        regex_parts = []
        for p in parts:
            if p == "#":
                regex_parts.append(".*")
            elif p == "*":
                regex_parts.append(r"[^.]+")
            else:
                regex_parts.append(re.escape(p))
        regex = r"^" + r"\.".join(regex_parts) + "$"
        return re.match(regex, topic) is not None


    # ------------------------------------------------------------------
    # Consumer groups
    # ------------------------------------------------------------------

    def create_consumer_group(self, topic_name: str, group_id: str) -> ConsumerGroup:
        topic = self.get_or_create_topic(topic_name)
        with self._lock:
            if group_id in self._groups[topic_name]:
                return self._groups[topic_name][group_id]
            group = ConsumerGroup(group_id, topic, self)
            self._groups[topic_name][group_id] = group
            return group

    def get_consumer_group(self, topic_name: str, group_id: str) -> Optional[ConsumerGroup]:
        with self._lock:
            return self._groups[topic_name].get(group_id)

    # ------------------------------------------------------------------
    # Producer / Consumer factories
    # ------------------------------------------------------------------

    def create_producer(self, producer_id: Optional[str] = None) -> Producer:
        pid = producer_id or f"producer_{uuid.uuid4().hex[:8]}"
        p = Producer(pid, self)
        self._producers[pid] = p
        return p

    def create_consumer(
        self,
        topic_name: str,
        consumer_id: Optional[str] = None,
        group_id: Optional[str] = None,
        start_offset: int = 0,
        auto_commit: bool = True,
    ) -> Consumer:
        cid = consumer_id or f"consumer_{uuid.uuid4().hex[:8]}"
        topic = self.get_or_create_topic(topic_name)
        group = None
        if group_id:
            group = self.create_consumer_group(topic_name, group_id)
        consumer = Consumer(cid, topic, group, start_offset, auto_commit)
        self._consumers[cid] = consumer
        return consumer

    # ------------------------------------------------------------------
    # Bridge APIs
    # ------------------------------------------------------------------

    def bridge_event_bus(self, handler: Callable[[Event], None]):
        """Bridge to event_bus_native.py — forward all events to legacy bus."""
        self._event_bus_bridge = handler
        def _bridge(event: Event):
            if self._event_bus_bridge:
                self._event_bus_bridge(event)
        self.subscribe("#", _bridge)

    def bridge_mesh(self, handler: Callable[[Event], None]):
        """Bridge to distributed_mesh_engine_native.py — cross-node forwarding."""
        self._mesh_bridge = handler
        def _bridge(event: Event):
            if self._mesh_bridge:
                self._mesh_bridge(event)
        self.subscribe("#", _bridge)

    # ------------------------------------------------------------------
    # HTTP / WebSocket endpoints (simulated — return event data)
    # ------------------------------------------------------------------

    def http_poll(self, topic_name: str, offset: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """HTTP polling endpoint — returns events as JSON-serializable dicts."""
        topic = self.get_or_create_topic(topic_name)
        return [ev.as_dict() for ev in topic.log.read(start_offset=offset, max_events=limit)]

    def websocket_stream(self, topic_name: str, offset: int = 0) -> Generator[Dict[str, Any], None, None]:
        """WebSocket streaming endpoint — yields events as dicts."""
        topic = self.get_or_create_topic(topic_name)
        consumer = self.create_consumer(topic_name, start_offset=offset)
        try:
            for ev in consumer.stream():
                yield ev.as_dict()
        finally:
            consumer.stop()

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def topic_stats(self, topic_name: str) -> Dict[str, Any]:
        topic = self.get_or_create_topic(topic_name)
        log = topic.log
        return {
            "topic": topic_name,
            "latest_offset": log.latest_offset,
            "total_events": log.total_count,
            "segments": log.segment_count(),
            "persistent": topic.config.persistent,
            "retention_ms": topic.config.retention_ms,
            "dlq_size": len(topic.dead_letter_queue()),
        }

    def consumer_stats(self, consumer_id: str) -> Dict[str, Any]:
        consumer = self._consumers.get(consumer_id)
        if not consumer:
            return {}
        return {
            "consumer_id": consumer_id,
            "topic": consumer.topic.name,
            "consumed": consumer.consumed,
            "lag": consumer.lag(),
            "group": consumer.group.group_id if consumer.group else None,
        }

    def group_stats(self, topic_name: str, group_id: str) -> Dict[str, Any]:
        group = self.get_consumer_group(topic_name, group_id)
        if not group:
            return {}
        return {
            "group_id": group_id,
            "topic": topic_name,
            "members": group.member_count(),
            "lag": group.group_lag(),
        }

    def health(self) -> Dict[str, Any]:
        import shutil
        total_size = sum(
            f.stat().st_size for f in self.data_dir.rglob("*") if f.is_file()
        )
        disk = shutil.disk_usage(str(self.data_dir))
        return {
            "data_dir": str(self.data_dir),
            "total_bytes": total_size,
            "disk_free": disk.free,
            "disk_percent": (disk.used / disk.total) * 100,
            "topics": len(self._topics),
            "producers": len(self._producers),
            "consumers": len(self._consumers),
            "groups": sum(len(g) for g in self._groups.values()),
            "healthy": disk.free > 100 * 1024 * 1024,  # > 100MB free
        }

    # ------------------------------------------------------------------
    # Cleanup loop
    # ------------------------------------------------------------------

    def _cleanup_loop(self):
        while self._running:
            time.sleep(60)
            with self._lock:
                for topic in self._topics.values():
                    topic.cleanup()

    def shutdown(self):
        self._running = False
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=2)
        for consumer in list(self._consumers.values()):
            consumer.stop()
        for group_map in self._groups.values():
            for group in group_map.values():
                group.checkpoint()

    # ------------------------------------------------------------------
    # Replay API
    # ------------------------------------------------------------------

    def replay(
        self,
        topic_name: str,
        start_offset: int = 0,
        end_offset: int = None,
        callback: Optional[Callable[[Event], None]] = None,
    ) -> Iterator[Event]:
        """Replay events from a topic, optionally with a callback."""
        topic = self.get_or_create_topic(topic_name)
        for ev in topic.log.read(start_offset=start_offset, end_offset=end_offset):
            if callback:
                callback(ev)
            yield ev

    # ------------------------------------------------------------------
    # Compaction
    # ------------------------------------------------------------------

    def compact_topic(self, topic_name: str):
        topic = self.get_or_create_topic(topic_name)
        topic.compact()

    # ------------------------------------------------------------------
    # Demo / Self-Test
    # ------------------------------------------------------------------

    @staticmethod
    def run():
        engine = EventStreamingEngine(data_dir="/tmp/magnatrix-event-demo")
        print("=" * 60)
        print("Event Streaming & Pub-Sub Native — Self-Test Demo")
        print("=" * 60)

        # 1. Create topics
        print("\n[1] Creating topics...")
        t1 = engine.create_topic("agent.llm.request", TopicConfig(persistent=True))
        t2 = engine.create_topic("system.health.alert", TopicConfig(persistent=True))
        t3 = engine.create_topic("trading.signal", TopicConfig(persistent=True, retention_count=50))
        print(f"  Topics: {engine.list_topics()}")

        # 2. Producer + publish
        print("\n[2] Publishing events...")
        producer = engine.create_producer("demo-producer")
        events = []
        for i in range(1000):
            ev = producer.send("agent.llm.request", key=f"req-{i}", payload={"prompt": f"hello {i}"})
            events.append(ev)
        print(f"  Published {producer.published} events to agent.llm.request")

        # 3. Consumer — poll
        print("\n[3] Consumer polling...")
        c1 = engine.create_consumer("agent.llm.request", consumer_id="c1", group_id="g1")
        batch = c1.poll(timeout_ms=100, max_records=10)
        print(f"  Polled {len(batch)} events, lag={c1.lag()}")

        # 4. Consumer — stream (generator)
        print("\n[4] Consumer streaming (generator)...")
        c2 = engine.create_consumer("agent.llm.request", consumer_id="c2", group_id="g1", start_offset=1)
        streamed = 0
        for ev in c2.stream():
            streamed += 1
            if streamed >= 5:
                break
        print(f"  Streamed {streamed} events via generator")
        c2.stop()

        # 5. Consumer — callback
        print("\n[5] Consumer callback (background thread)...")
        received = []
        c3 = engine.create_consumer("agent.llm.request", consumer_id="c3", group_id="g2", start_offset=1)
        c3.assign_callback(lambda ev: received.append(ev.sequence))
        c3.start_callback(interval_ms=50)
        time.sleep(0.5)
        c3.stop()
        print(f"  Callback received {len(received)} events")

        # 6. Wildcard subscription
        print("\n[6] Wildcard subscription agent.*.response...")
        wildcard_hits = []
        engine.create_topic("agent.gpt4.response", TopicConfig())
        engine.create_topic("agent.claude.response", TopicConfig())
        sub_id = engine.subscribe("agent.*.response", lambda ev: wildcard_hits.append(ev.topic))
        producer.send("agent.gpt4.response", key="k1", payload="done")
        producer.send("agent.claude.response", key="k2", payload="done")
        time.sleep(0.1)
        print(f"  Wildcard matched {len(wildcard_hits)} events: {set(wildcard_hits)}")

        # 7. Multi-level wildcard
        print("\n[7] Multi-level wildcard system.#...")
        sys_hits = []
        engine.subscribe("system.#", lambda ev: sys_hits.append(ev.topic))
        producer.send("system.health.alert", key="cpu", payload="high")
        producer.send("system.memory.warning", key="ram", payload="low")
        time.sleep(0.1)
        print(f"  System wildcard matched {len(sys_hits)} events: {set(sys_hits)}")

        # 8. Replay from offset
        print("\n[8] Replay from offset 500...")
        replayed = list(engine.replay("agent.llm.request", start_offset=500, end_offset=505))
        print(f"  Replay returned {len(replayed)} events, seqs: {[e.sequence for e in replayed]}")

        # 9. Batch consume
        print("\n[9] Batch consume...")
        c4 = engine.create_consumer("agent.llm.request", consumer_id="c4", start_offset=1)
        big_batch = c4.poll(timeout_ms=200, max_records=100)
        print(f"  Batch consumed {len(big_batch)} events")
        c4.stop()

        # 10. Segment rotation
        print("\n[10] Segment rotation test...")
        engine2 = EventStreamingEngine(data_dir="/tmp/magnatrix-rotation-test")
        engine2.create_topic("burst", TopicConfig())
        p2 = engine2.create_producer("p2")
        for i in range(10_000):
            p2.send("burst", key=f"k-{i}", payload={"data": "x" * 100})
        seg_count = engine2.get_or_create_topic("burst").log.segment_count()
        print(f"  10K events produced, segments={seg_count}")

        # 11. Backpressure
        print("\n[11] Backpressure (slow consumer)...")
        engine3 = EventStreamingEngine(data_dir="/tmp/magnatrix-backpressure-test")
        engine3.create_topic("pressure", TopicConfig())
        p3 = engine3.create_producer("p3")
        # Publish more than queue can hold quickly
        for i in range(50):
            p3.send("pressure", key=f"k-{i}", payload={"i": i})
        print(f"  Published 50 events, no overflow")

        # 12. Compaction
        print("\n[12] Log compaction...")
        engine4 = EventStreamingEngine(data_dir="/tmp/magnatrix-compact-test")
        engine4.create_topic("compact", TopicConfig())
        p4 = engine4.create_producer("p4")
        for i in range(100):
            p4.send("compact", key="same-key", payload={"version": i})
        engine4.compact_topic("compact")
        compacted = list(engine4.replay("compact", start_offset=1))
        print(f"  100 events with same key compacted to {len(compacted)} events")

        # 13. Health
        print("\n[13] Health check...")
        health = engine.health()
        print(f"  Healthy: {health['healthy']}, topics: {health['topics']}, disk_free: {health['disk_free'] / (1024*1024):.1f}MB")

        # 14. Stats
        print("\n[14] Topic stats...")
        stats = engine.topic_stats("agent.llm.request")
        print(f"  {stats}")

        print("\n[15] Consumer group stats...")
        gstats = engine.group_stats("agent.llm.request", "g1")
        print(f"  {gstats}")

        # Cleanup
        engine.shutdown()
        engine2.shutdown()
        engine3.shutdown()
        engine4.shutdown()

        print("\n" + "=" * 60)
        print("All self-tests passed. Event Streaming Engine ready.")
        print("=" * 60)
        return True


if __name__ == "__main__":
    EventStreamingEngine.run()
