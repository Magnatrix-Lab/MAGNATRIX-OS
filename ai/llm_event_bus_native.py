#!/usr/bin/env python3
"""
MAGNATRIX-OS — Event Bus / Pub-Sub Backbone
ai/llm_event_bus_native.py

Features:
- Topic-based pub/sub messaging
- Event routing with filtering (wildcard topics, conditional routing)
- Async event handlers with worker pool simulation
- Event persistence / replay capability
- Dead letter queue for failed events

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import queue
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("event_bus")


class EventPriority(enum.Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


class EventStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass
class Event:
    id: str
    topic: str
    payload: Any
    priority: EventPriority = EventPriority.NORMAL
    timestamp: float = 0.0
    retries: int = 0
    max_retries: int = 3
    status: EventStatus = EventStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.monotonic()


@dataclass
class Subscription:
    id: str
    topic_pattern: str
    handler: Callable[[Event], None]
    priority: EventPriority = EventPriority.NORMAL
    filter_fn: Optional[Callable[[Event], bool]] = None
    max_concurrent: int = 1


class TopicMatcher:
    """Match topics with wildcards."""

    @staticmethod
    def match(topic: str, pattern: str) -> bool:
        if pattern == "*":
            return True
        if pattern == topic:
            return True
        # Handle * wildcard (e.g., "llm.*" matches "llm.inference")
        parts_p = pattern.split(".")
        parts_t = topic.split(".")
        if len(parts_p) != len(parts_t):
            # Allow trailing * to match any sub-topics
            if parts_p[-1] == "*" and len(parts_p) <= len(parts_t):
                prefix_ok = all(pp == pt or pp == "*" for pp, pt in zip(parts_p[:-1], parts_t[:len(parts_p)-1]))
                return prefix_ok
            return False
        return all(pp == pt or pp == "*" for pp, pt in zip(parts_p, parts_t))


class EventStore:
    """In-memory event persistence with replay."""

    def __init__(self, max_events: int = 10000):
        self._events: deque = deque(maxlen=max_events)
        self._lock = threading.Lock()

    def append(self, event: Event) -> None:
        with self._lock:
            self._events.append(event)

    def replay(self, topic_pattern: str = "*", since: float = 0.0) -> List[Event]:
        with self._lock:
            return [
                e for e in self._events
                if TopicMatcher.match(e.topic, topic_pattern) and e.timestamp >= since
            ]

    def get_recent(self, n: int = 100) -> List[Event]:
        with self._lock:
            return list(self._events)[-n:]

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


class DeadLetterQueue:
    """Queue for failed events that exhausted retries."""

    def __init__(self, max_size: int = 1000):
        self._queue: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def push(self, event: Event, reason: str) -> None:
        event.status = EventStatus.DEAD_LETTER
        event.metadata["dead_letter_reason"] = reason
        with self._lock:
            self._queue.append(event)
        logger.warning(f"Event {event.id} moved to dead letter queue: {reason}")

    def list_all(self) -> List[Event]:
        with self._lock:
            return list(self._queue)

    def replay(self, handler: Callable[[Event], None]) -> int:
        count = 0
        with self._lock:
            for event in list(self._queue):
                event.status = EventStatus.PENDING
                event.retries = 0
                handler(event)
                count += 1
            self._queue.clear()
        return count


class EventBus:
    """Pub/Sub event bus with routing and filtering."""

    def __init__(self, workers: int = 4, queue_size: int = 1000):
        self._subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self._store = EventStore()
        self._dlq = DeadLetterQueue()
        self._task_queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=queue_size)
        self._workers = workers
        self._worker_threads: List[threading.Thread] = []
        self._shutdown = threading.Event()
        self._lock = threading.RLock()
        self._counter = 0
        self._stats = {"published": 0, "delivered": 0, "failed": 0, "dlq": 0}
        self._start_workers()

    def _start_workers(self) -> None:
        for i in range(self._workers):
            t = threading.Thread(target=self._worker_loop, name=f"event-worker-{i}", daemon=True)
            t.start()
            self._worker_threads.append(t)

    def _worker_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                _, _, event, sub = self._task_queue.get(timeout=0.5)
                self._process(event, sub)
            except queue.Empty:
                continue

    def _process(self, event: Event, sub: Subscription) -> None:
        try:
            event.status = EventStatus.PROCESSING
            if sub.filter_fn and not sub.filter_fn(event):
                return
            sub.handler(event)
            event.status = EventStatus.COMPLETED
            self._stats["delivered"] += 1
        except Exception as e:
            event.retries += 1
            self._stats["failed"] += 1
            if event.retries >= event.max_retries:
                self._dlq.push(event, f"Max retries exceeded: {e}")
                self._stats["dlq"] += 1
            else:
                # Re-queue with delay
                time.sleep(0.01 * event.retries)
                self._task_queue.put((sub.priority.value, self._counter, event, sub))
                self._counter += 1

    def subscribe(self, topic_pattern: str, handler: Callable[[Event], None],
                  priority: EventPriority = EventPriority.NORMAL,
                  filter_fn: Optional[Callable[[Event], bool]] = None) -> str:
        sub_id = str(uuid.uuid4())[:8]
        sub = Subscription(
            id=sub_id, topic_pattern=topic_pattern, handler=handler,
            priority=priority, filter_fn=filter_fn,
        )
        with self._lock:
            self._subscriptions[topic_pattern].append(sub)
        logger.info(f"Subscribed {sub_id} to '{topic_pattern}'")
        return sub_id

    def unsubscribe(self, sub_id: str) -> bool:
        with self._lock:
            for topic, subs in self._subscriptions.items():
                for i, sub in enumerate(subs):
                    if sub.id == sub_id:
                        subs.pop(i)
                        return True
        return False

    def publish(self, topic: str, payload: Any, priority: EventPriority = EventPriority.NORMAL,
                metadata: Optional[Dict[str, Any]] = None) -> str:
        event = Event(
            id=str(uuid.uuid4())[:8], topic=topic, payload=payload,
            priority=priority, metadata=metadata or {},
        )
        self._store.append(event)
        self._stats["published"] += 1

        with self._lock:
            matching = []
            for pattern, subs in self._subscriptions.items():
                if TopicMatcher.match(topic, pattern):
                    matching.extend(subs)

        for sub in matching:
            try:
                self._task_queue.put((sub.priority.value, self._counter, event, sub), block=False)
                self._counter += 1
            except queue.Full:
                logger.warning(f"Event queue full, dropping event {event.id}")

        return event.id

    def replay(self, topic_pattern: str = "*", since: float = 0.0) -> int:
        events = self._store.replay(topic_pattern, since)
        count = 0
        for event in events:
            event.status = EventStatus.PENDING
            event.retries = 0
            self.publish(event.topic, event.payload, event.priority, event.metadata)
            count += 1
        return count

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)

    def get_dead_letter_events(self) -> List[Event]:
        return self._dlq.list_all()

    def shutdown(self) -> None:
        self._shutdown.set()
        for t in self._worker_threads:
            t.join(timeout=1.0)


class EventBusEngine:
    """Unified event bus engine."""

    def __init__(self, workers: int = 4):
        self.bus = EventBus(workers=workers)
        self._handlers: Dict[str, Callable] = {}

    def on(self, topic_pattern: str, handler: Callable[[Event], None],
           priority: EventPriority = EventPriority.NORMAL,
           filter_fn: Optional[Callable[[Event], bool]] = None) -> str:
        return self.bus.subscribe(topic_pattern, handler, priority, filter_fn)

    def off(self, sub_id: str) -> bool:
        return self.bus.unsubscribe(sub_id)

    def emit(self, topic: str, payload: Any, priority: EventPriority = EventPriority.NORMAL) -> str:
        return self.bus.publish(topic, payload, priority)

    def replay(self, topic_pattern: str = "*", since: float = 0.0) -> int:
        return self.bus.replay(topic_pattern, since)

    def get_dlq(self) -> List[Event]:
        return self.bus.get_dead_letter_events()

    def get_status(self) -> Dict[str, Any]:
        return self.bus.get_stats()


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Event Bus / Pub-Sub Backbone")
    print("ai/llm_event_bus_native.py")
    print("=" * 60)

    engine = EventBusEngine(workers=2)
    received = []

    def handler_a(event: Event) -> None:
        received.append(f"A:{event.topic}:{event.payload}")

    def handler_b(event: Event) -> None:
        received.append(f"B:{event.topic}:{event.payload}")

    def failing_handler(event: Event) -> None:
        raise RuntimeError("Simulated failure")

    # 1. Subscribe
    print("")
    print("[1] Subscribe to topics")
    sub1 = engine.on("llm.inference", handler_a, EventPriority.HIGH)
    sub2 = engine.on("llm.training", handler_b, EventPriority.NORMAL)
    sub3 = engine.on("llm.*", handler_a, EventPriority.NORMAL)  # wildcard
    print(f"  Subscribed: {sub1}, {sub2}, {sub3}")

    # 2. Publish events
    print("")
    print("[2] Publish Events")
    engine.emit("llm.inference", {"model": "arena-v1", "tokens": 150}, EventPriority.HIGH)
    engine.emit("llm.training", {"epoch": 5, "loss": 0.23}, EventPriority.NORMAL)
    engine.emit("llm.evaluation", {"accuracy": 0.94}, EventPriority.LOW)
    time.sleep(0.3)  # Let workers process
    print(f"  Events received: {len(received)}")
    for r in received[:5]:
        print(f"    {r}")

    # 3. Filtered subscription
    print("")
    print("[3] Filtered Subscription")
    filtered_received = []
    def filtered_handler(event: Event) -> None:
        filtered_received.append(event.payload)
    engine.on("llm.metrics", filtered_handler, filter_fn=lambda e: e.payload.get("cpu") > 80)
    engine.emit("llm.metrics", {"cpu": 45, "memory": 60})
    engine.emit("llm.metrics", {"cpu": 92, "memory": 85})
    time.sleep(0.2)
    print(f"  Filtered received: {len(filtered_received)} (should be 1, cpu > 80)")
    print(f"    {filtered_received}")

    # 4. Dead letter queue
    print("")
    print("[4] Dead Letter Queue")
    sub_dlq = engine.on("llm.danger", failing_handler)
    engine.emit("llm.danger", {"action": "delete-all"})
    time.sleep(0.5)
    dlq = engine.get_dlq()
    print(f"  DLQ events: {len(dlq)}")
    for e in dlq:
        print(f"    {e.id}: {e.metadata.get('dead_letter_reason', '')}")

    # 5. Replay
    print("")
    print("[5] Event Replay")
    replay_count = engine.replay("llm.inference")
    time.sleep(0.2)
    print(f"  Replayed {replay_count} events")

    # 6. Stats
    print("")
    print("[6] Event Bus Stats")
    stats = engine.get_status()
    print(f"  {stats}")

    engine.bus.shutdown()

    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
