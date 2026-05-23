"""event_bus.py — MAGNATRIX-OS Layer 7: Event Bus Foundation.

Centralized pub/sub engine dengan topic-based routing, wildcards,
priority queue, dead letter queue, event persistence, dan cross-layer routing.

Pure Python, zero external dependencies.
Author: GQRIS (MAGNATRIX-OS)
"""
from __future__ import annotations

import json
import queue
import re
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 — Event Model & Enums
# ═══════════════════════════════════════════════════════════════════════════════

class EventPriority(Enum):
    """Priority levels untuk event processing."""
    CRITICAL = 0   # System-level, immediate
    HIGH = 1       # Urgent operational
    NORMAL = 2     # Default
    LOW = 3        # Background tasks
    BATCH = 4      # Deferred processing

    def __repr__(self) -> str:
        return f"EventPriority.{self.name}"


class EventStatus(Enum):
    """Lifecycle status untuk event."""
    PENDING = auto()
    PROCESSING = auto()
    DELIVERED = auto()
    FAILED = auto()
    DEAD_LETTER = auto()
    RETRYING = auto()

    def __repr__(self) -> str:
        return f"EventStatus.{self.name}"


@dataclass
class Event:
    """Core event dataclass."""
    id: str
    topic: str
    payload: Dict[str, Any]
    timestamp: float
    source_layer: int
    priority: EventPriority = EventPriority.NORMAL
    status: EventStatus = EventStatus.PENDING
    delivery_attempts: int = 0
    max_retries: int = 3
    target_layers: Optional[List[int]] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (f"Event({self.id[:8]}, topic='{self.topic}', "
                f"layer={self.source_layer}, prio={self.priority.name})")

    @classmethod
    def create(
        cls,
        topic: str,
        payload: Dict[str, Any],
        source_layer: int = 0,
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: Optional[str] = None,
        target_layers: Optional[List[int]] = None,
    ) -> Event:
        """Factory method untuk create event baru."""
        return cls(
            id=str(uuid.uuid4()),
            topic=topic,
            payload=payload,
            timestamp=time.time(),
            source_layer=source_layer,
            priority=priority,
            correlation_id=correlation_id or str(uuid.uuid4()),
            target_layers=target_layers,
        )


@dataclass
class Subscription:
    """Subscriber registration record."""
    id: str
    topic_pattern: str
    callback: Callable[[Event], None]
    priority_filter: Optional[Set[EventPriority]] = None
    source_layer_filter: Optional[Set[int]] = None
    max_concurrent: int = 1
    active: bool = True
    created_at: float = field(default_factory=time.time)
    deliver_count: int = 0
    error_count: int = 0

    def __repr__(self) -> str:
        return f"Subscription({self.id[:8]}, pattern='{self.topic_pattern}', active={self.active})"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2 — Topic Router (Wildcard Matching)
# ═══════════════════════════════════════════════════════════════════════════════

class TopicRouter:
    """
    Topic router dengan wildcard support:
    - `*` match single level (e.g., `trading.*.btc`)
    - `#` match multi level (e.g., `trading.#`)
    - Exact match untuk topic tanpa wildcard
    """

    def __init__(self) -> None:
        self._exact: Dict[str, Set[str]] = {}
        self._wildcard_single: Dict[str, Set[str]] = {}  # *
        self._wildcard_multi: Dict[str, Set[str]] = {}    # #
        self._lock = threading.RLock()

    def __repr__(self) -> str:
        return f"TopicRouter(exact={len(self._exact)}, wildcards={len(self._wildcard_single)+len(self._wildcard_multi)})"

    def register(self, topic_pattern: str, subscription_id: str) -> None:
        """Register subscription ke routing table."""
        with self._lock:
            if "#" in topic_pattern:
                self._wildcard_multi.setdefault(topic_pattern, set()).add(subscription_id)
            elif "*" in topic_pattern:
                self._wildcard_single.setdefault(topic_pattern, set()).add(subscription_id)
            else:
                self._exact.setdefault(topic_pattern, set()).add(subscription_id)

    def unregister(self, topic_pattern: str, subscription_id: str) -> None:
        """Remove subscription dari routing table."""
        with self._lock:
            for table in (self._exact, self._wildcard_single, self._wildcard_multi):
                if topic_pattern in table:
                    table[topic_pattern].discard(subscription_id)
                    if not table[topic_pattern]:
                        del table[topic_pattern]

    def match(self, topic: str) -> Set[str]:
        """Find all subscription IDs yang match topic."""
        matched: Set[str] = set()
        with self._lock:
            # Exact match
            if topic in self._exact:
                matched.update(self._exact[topic])

            # Single wildcard match
            for pattern, ids in self._wildcard_single.items():
                if self._match_single(pattern, topic):
                    matched.update(ids)

            # Multi wildcard match
            for pattern, ids in self._wildcard_multi.items():
                if self._match_multi(pattern, topic):
                    matched.update(ids)

        return matched

    @staticmethod
    def _match_single(pattern: str, topic: str) -> bool:
        """Match pattern dengan single-level wildcard *."""
        pattern_parts = pattern.split(".")
        topic_parts = topic.split(".")
        if len(pattern_parts) != len(topic_parts):
            return False
        for p, t in zip(pattern_parts, topic_parts):
            if p != "*" and p != t:
                return False
        return True

    @staticmethod
    def _match_multi(pattern: str, topic: str) -> bool:
        """Match pattern dengan multi-level wildcard #."""
        # # harus di posisi akhir
        if not pattern.endswith(".#"):
            return False
        prefix = pattern[:-2]  # Hapus .#
        if not prefix:
            return True  # # match everything
        return topic.startswith(prefix + ".") or topic == prefix


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 — Priority Event Queue
# ═══════════════════════════════════════════════════════════════════════════════

class PriorityEventQueue:
    """
    Priority queue untuk event processing.
    Lower priority value = higher urgency.
    """

    def __init__(self, maxsize: int = 0) -> None:
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=maxsize)
        self._counter = 0
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return f"PriorityEventQueue(size={self._queue.qsize()})"

    def put(self, event: Event) -> None:
        """Enqueue event dengan priority ordering."""
        with self._lock:
            self._counter += 1
            # Tuple: (priority_value, sequence_counter, event)
            # Counter untuk preserve FIFO dalam priority yang sama
            self._queue.put((event.priority.value, self._counter, event))

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Event]:
        """Dequeue event dengan highest priority."""
        try:
            _priority, _counter, event = self._queue.get(block=block, timeout=timeout)
            return event
        except queue.Empty:
            return None

    def qsize(self) -> int:
        return self._queue.qsize()

    def empty(self) -> bool:
        return self._queue.empty()


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 — Dead Letter Queue (DLQ)
# ═══════════════════════════════════════════════════════════════════════════════

class DeadLetterQueue:
    """
    Dead Letter Queue untuk event yang gagal deliver setelah max retries.
    Support reprocessing dan analytics.
    """

    def __init__(self, max_entries: int = 1000) -> None:
        self.max_entries = max_entries
        self._entries: List[Tuple[Event, str, float]] = []  # (event, reason, timestamp)
        self._lock = threading.RLock()

    def __repr__(self) -> str:
        return f"DeadLetterQueue(entries={len(self._entries)}/{self.max_entries})"

    def add(self, event: Event, reason: str) -> None:
        """Add failed event ke DLQ."""
        with self._lock:
            event.status = EventStatus.DEAD_LETTER
            entry = (event, reason, time.time())
            self._entries.append(entry)
            if len(self._entries) > self.max_entries:
                self._entries.pop(0)  # Evict oldest

    def list(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List dead letter entries."""
        with self._lock:
            entries = self._entries[-limit:]
        return [
            {
                "event_id": e.id,
                "topic": e.topic,
                "reason": reason,
                "timestamp": ts,
                "attempts": e.delivery_attempts,
            }
            for e, reason, ts in entries
        ]

    def reprocess(self, event_id: str, event_bus: EventBusNative) -> bool:
        """Reprocess dead letter event."""
        with self._lock:
            for idx, (event, reason, ts) in enumerate(self._entries):
                if event.id == event_id:
                    event.status = EventStatus.RETRYING
                    event.delivery_attempts = 0
                    del self._entries[idx]
                    event_bus.publish_event(event)
                    return True
        return False

    def stats(self) -> Dict[str, Any]:
        """Return DLQ statistics."""
        with self._lock:
            topics: Dict[str, int] = {}
            for event, _reason, _ts in self._entries:
                topics[event.topic] = topics.get(event.topic, 0) + 1
            return {
                "total_entries": len(self._entries),
                "max_entries": self.max_entries,
                "topics": topics,
                "oldest": self._entries[0][2] if self._entries else None,
                "newest": self._entries[-1][2] if self._entries else None,
            }


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5 — Event Persistence (SQLite-Backed)
# ═══════════════════════════════════════════════════════════════════════════════

class EventPersistence:
    """
    SQLite-backed event persistence untuk audit trail, replay,
    dan recovery setelah crash.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._init_db()

    def __repr__(self) -> str:
        return f"EventPersistence(db={self.db_path})"

    def _init_db(self) -> None:
        """Initialize SQLite schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    source_layer INTEGER NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    correlation_id TEXT,
                    delivery_attempts INTEGER DEFAULT 0,
                    target_layers TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_topic ON events(topic)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_correlation ON events(correlation_id)
            """)
            conn.commit()

    def save(self, event: Event) -> None:
        """Persist event ke database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO events
                (id, topic, payload, timestamp, source_layer, priority, status,
                 correlation_id, delivery_attempts, target_layers, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.topic,
                    json.dumps(event.payload, default=str),
                    event.timestamp,
                    event.source_layer,
                    event.priority.name,
                    event.status.name,
                    event.correlation_id,
                    event.delivery_attempts,
                    json.dumps(event.target_layers) if event.target_layers else None,
                    json.dumps(event.metadata, default=str),
                ),
            )
            conn.commit()

    def load_range(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        topic: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Load events dari database dengan filter."""
        conditions = ["1=1"]
        params: List[Any] = []
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        if topic:
            conditions.append("topic = ?")
            params.append(topic)

        query = f"SELECT * FROM events WHERE {' AND '.join(conditions)} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        events = []
        for row in rows:
            events.append(self._row_to_event(row))
        return events

    def get_by_correlation(self, correlation_id: str) -> List[Event]:
        """Get semua event dengan correlation ID yang sama."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM events WHERE correlation_id = ? ORDER BY timestamp",
                (correlation_id,),
            ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def _row_to_event(self, row: sqlite3.Row) -> Event:
        """Convert database row ke Event object."""
        return Event(
            id=row["id"],
            topic=row["topic"],
            payload=json.loads(row["payload"]),
            timestamp=row["timestamp"],
            source_layer=row["source_layer"],
            priority=EventPriority[row["priority"]],
            status=EventStatus[row["status"]],
            correlation_id=row["correlation_id"],
            delivery_attempts=row["delivery_attempts"],
            target_layers=json.loads(row["target_layers"]) if row["target_layers"] else None,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6 — Cross-Layer Event Router
# ═══════════════════════════════════════════════════════════════════════════════

class CrossLayerRouter:
    """
    Router khusus untuk cross-layer event routing.
    Filter event berdasarkan source_layer dan target_layers.
    """

    def __init__(self) -> None:
        self._layer_routes: Dict[Tuple[int, int], Set[str]] = {}
        self._broadcast_routes: Dict[int, Set[str]] = {}
        self._lock = threading.RLock()

    def __repr__(self) -> str:
        return f"CrossLayerRouter(routes={len(self._layer_routes)}, broadcasts={len(self._broadcast_routes)})"

    def register_route(self, from_layer: int, to_layer: int, subscription_id: str) -> None:
        """Register route dari layer ke layer."""
        with self._lock:
            key = (from_layer, to_layer)
            self._layer_routes.setdefault(key, set()).add(subscription_id)

    def register_broadcast(self, from_layer: int, subscription_id: str) -> None:
        """Register broadcast listener untuk layer."""
        with self._lock:
            self._broadcast_routes.setdefault(from_layer, set()).add(subscription_id)

    def unregister(self, subscription_id: str) -> None:
        """Remove subscription dari semua routes."""
        with self._lock:
            for key in list(self._layer_routes.keys()):
                self._layer_routes[key].discard(subscription_id)
                if not self._layer_routes[key]:
                    del self._layer_routes[key]
            for layer in list(self._broadcast_routes.keys()):
                self._broadcast_routes[layer].discard(subscription_id)
                if not self._broadcast_routes[layer]:
                    del self._broadcast_routes[layer]

    def route(self, event: Event) -> Set[str]:
        """Determine subscriptions yang eligible untuk event ini."""
        matched: Set[str] = set()
        src = event.source_layer
        targets = event.target_layers

        with self._lock:
            # Jika ada target_layers spesifik
            if targets:
                for tgt in targets:
                    matched.update(self._layer_routes.get((src, tgt), set()))
                    # Juga cek broadcast ke target
                    matched.update(self._broadcast_routes.get(tgt, set()))
            else:
                # Broadcast: semua yang listen ke source layer
                matched.update(self._broadcast_routes.get(src, set()))
                # Juga semua routes dari source ke any
                for (f, t), ids in self._layer_routes.items():
                    if f == src:
                        matched.update(ids)

        return matched


# ═══════════════════════════════════════════════════════════════════════════════
# Section 7 — EventBusNative (Main Orchestrator)
# ═══════════════════════════════════════════════════════════════════════════════

class EventBusNative:
    """
    Centralized pub/sub event bus untuk MAGNATRIX-OS.
    Menggabungkan topic routing, priority queue, DLQ, persistence,
    dan cross-layer routing dalam satu engine.
    """

    def __init__(self, persistence_db: Optional[str] = None, max_workers: int = 4) -> None:
        self.persistence = EventPersistence(persistence_db or ":memory:")
        self.topic_router = TopicRouter()
        self.cross_router = CrossLayerRouter()
        self.priority_queue = PriorityEventQueue()
        self.dlq = DeadLetterQueue()
        self.subscriptions: Dict[str, Subscription] = {}
        self._running = False
        self._dispatcher_thread: Optional[threading.Thread] = None
        self._max_workers = max_workers
        self._stats: Dict[str, Any] = {
            "published": 0,
            "delivered": 0,
            "failed": 0,
            "dlq": 0,
        }
        self._lock = threading.RLock()

    def __repr__(self) -> str:
        return (f"EventBusNative(subs={len(self.subscriptions)}, "
                f"queue={self.priority_queue.qsize()}, dlq={len(self.dlq._entries)})")

    def subscribe(
        self,
        topic_pattern: str,
        callback: Callable[[Event], None],
        priority_filter: Optional[Set[EventPriority]] = None,
        source_layer_filter: Optional[Set[int]] = None,
        listen_from_layer: Optional[int] = None,
        listen_to_layer: Optional[int] = None,
    ) -> str:
        """
        Subscribe ke topic pattern.
        Return subscription ID.
        """
        sub_id = str(uuid.uuid4())
        sub = Subscription(
            id=sub_id,
            topic_pattern=topic_pattern,
            callback=callback,
            priority_filter=priority_filter,
            source_layer_filter=source_layer_filter,
        )
        with self._lock:
            self.subscriptions[sub_id] = sub
            self.topic_router.register(topic_pattern, sub_id)
            if listen_from_layer is not None and listen_to_layer is not None:
                self.cross_router.register_route(listen_from_layer, listen_to_layer, sub_id)
            elif listen_from_layer is not None:
                self.cross_router.register_broadcast(listen_from_layer, sub_id)
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe by ID."""
        with self._lock:
            sub = self.subscriptions.pop(subscription_id, None)
            if sub:
                self.topic_router.unregister(sub.topic_pattern, subscription_id)
                self.cross_router.unregister(subscription_id)
                return True
            return False

    def list_subscriptions(self) -> List[Dict[str, Any]]:
        """List semua subscriptions."""
        with self._lock:
            return [
                {
                    "id": s.id[:8],
                    "pattern": s.topic_pattern,
                    "active": s.active,
                    "deliveries": s.deliver_count,
                    "errors": s.error_count,
                }
                for s in self.subscriptions.values()
            ]

    def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        source_layer: int = 0,
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: Optional[str] = None,
        target_layers: Optional[List[int]] = None,
    ) -> str:
        """Publish event ke bus. Return event ID."""
        event = Event.create(
            topic=topic,
            payload=payload,
            source_layer=source_layer,
            priority=priority,
            correlation_id=correlation_id,
            target_layers=target_layers,
        )
        self.publish_event(event)
        return event.id

    def publish_event(self, event: Event) -> None:
        """Publish pre-constructed event."""
        with self._lock:
            self._stats["published"] += 1
        self.persistence.save(event)
        self.priority_queue.put(event)

    def start(self) -> None:
        """Start event dispatcher thread."""
        self._running = True
        self._dispatcher_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._dispatcher_thread.start()

    def stop(self) -> None:
        """Stop event dispatcher."""
        self._running = False
        if self._dispatcher_thread and self._dispatcher_thread.is_alive():
            self._dispatcher_thread.join(timeout=2.0)

    def _dispatch_loop(self) -> None:
        """Background dispatcher: dequeue dan deliver ke subscribers."""
        while self._running:
            event = self.priority_queue.get(block=True, timeout=0.5)
            if event is None:
                continue
            self._deliver(event)

    def _deliver(self, event: Event) -> None:
        """Deliver event ke semua matching subscribers."""
        event.status = EventStatus.PROCESSING
        event.delivery_attempts += 1

        # Find matching subscriptions
        topic_matches = self.topic_router.match(event.topic)
        cross_matches = self.cross_router.route(event)
        all_matches = topic_matches | cross_matches

        delivered = 0
        for sub_id in all_matches:
            sub = self.subscriptions.get(sub_id)
            if not sub or not sub.active:
                continue

            # Apply filters
            if sub.priority_filter and event.priority not in sub.priority_filter:
                continue
            if sub.source_layer_filter and event.source_layer not in sub.source_layer_filter:
                continue

            # Deliver
            try:
                sub.callback(event)
                sub.deliver_count += 1
                delivered += 1
            except Exception as e:
                sub.error_count += 1
                event.error_log = getattr(event, "error_log", [])
                event.error_log.append(str(e))

        # Update status
        if delivered > 0:
            event.status = EventStatus.DELIVERED
            with self._lock:
                self._stats["delivered"] += 1
        else:
            if event.delivery_attempts >= event.max_retries:
                event.status = EventStatus.FAILED
                self.dlq.add(event, f"Max retries ({event.max_retries}) exceeded")
                with self._lock:
                    self._stats["failed"] += 1
                    self._stats["dlq"] += 1
            else:
                event.status = EventStatus.RETRYING
                # Requeue dengan delay (simplified: langsung requeue)
                self.priority_queue.put(event)

        self.persistence.save(event)

    def get_stats(self) -> Dict[str, Any]:
        """Return delivery statistics."""
        with self._lock:
            return self._stats.copy()

    def get_event_history(
        self,
        topic: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return persisted event history."""
        events = self.persistence.load_range(topic=topic, limit=limit)
        return [
            {
                "id": e.id[:8],
                "topic": e.topic,
                "priority": e.priority.name,
                "status": e.status.name,
                "source_layer": e.source_layer,
                "timestamp": e.timestamp,
            }
            for e in events
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# Section 8 — Demo
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  MAGNATRIX-OS Layer 7 — EventBusNative Demo")
    print("  Pure Python | Zero External Dependencies")
    print("=" * 70)

    # Tracking untuk demo
    delivery_log: List[str] = []
    delivered_events: Dict[str, int] = {}

    def make_handler(name: str):
        def handler(event: Event) -> None:
            msg = f"[{name}] received '{event.topic}' from layer {event.source_layer}"
            delivery_log.append(msg)
            delivered_events[name] = delivered_events.get(name, 0) + 1
            print(f"  📨 {msg}")
        return handler

    # 1. Initialize EventBus
    bus = EventBusNative(persistence_db=":memory:")
    print(f"\n[INIT] {bus}")

    # 2. Subscribe 3 subscribers dengan patterns berbeda
    sub1 = bus.subscribe("trading.btc.*", make_handler("Subscriber-A"))
    sub2 = bus.subscribe("trading.#", make_handler("Subscriber-B"))
    sub3 = bus.subscribe("system.alert", make_handler("Subscriber-C"))
    print(f"\n[SUBSCRIBE] 3 subscribers registered:")
    for sub in bus.list_subscriptions():
        print(f"  - {sub['id']} | pattern='{sub['pattern']}' | active={sub['active']}")

    # 3. Start dispatcher
    bus.start()
    print(f"\n[START] Dispatcher thread running")

    # 4. Publish 10 events
    print(f"\n[PUBLISH] Publishing 10 events...")
    event_ids = []
    events_data = [
        ("trading.btc.price", {"price": 65000, "change": 1.2}, 11, EventPriority.HIGH),
        ("trading.btc.volume", {"volume": 1200, "period": "1h"}, 11, EventPriority.NORMAL),
        ("trading.eth.price", {"price": 3500, "change": -0.5}, 11, EventPriority.HIGH),
        ("system.alert", {"level": "warning", "msg": "Memory > 80%"}, 0, EventPriority.CRITICAL),
        ("trading.btc.order", {"side": "buy", "amount": 0.5}, 11, EventPriority.NORMAL),
        ("network.p2p.peer_joined", {"peer_id": "abc123", "region": "ap-southeast"}, 13, EventPriority.LOW),
        ("system.alert", {"level": "error", "msg": "Disk > 95%"}, 2, EventPriority.CRITICAL),
        ("trading.btc.signal", {"signal": "bullish", "confidence": 0.82}, 11, EventPriority.HIGH),
        ("agent.runtime.task_complete", {"task_id": "t42", "result": "ok"}, 9, EventPriority.NORMAL),
        ("trading.btc.price", {"price": 65100, "change": 0.15}, 11, EventPriority.HIGH),
    ]

    for topic, payload, layer, prio in events_data:
        eid = bus.publish(topic, payload, source_layer=layer, priority=prio)
        event_ids.append(eid)
        print(f"  📤 Published '{topic}' (layer={layer}, prio={prio.name}) -> {eid[:8]}")

    # 5. Tunggu delivery selesai
    time.sleep(1.5)
    print(f"\n[DELIVERY] Waiting for delivery...")

    # 6. Stats
    stats = bus.get_stats()
    print(f"\n[STATS] Delivery statistics:")
    print(f"  Published:  {stats['published']}")
    print(f"  Delivered:  {stats['delivered']}")
    print(f"  Failed:     {stats['failed']}")
    print(f"  DLQ:        {stats['dlq']}")

    # 7. Per-subscriber delivery count
    print(f"\n[SUBSCRIBER COUNTS]")
    for name, count in sorted(delivered_events.items()):
        print(f"  {name}: {count} events")

    # 8. Event history dari persistence
    print(f"\n[PERSISTENCE] Event history (last 10):")
    history = bus.get_event_history(limit=10)
    for h in history:
        ts = time.strftime("%H:%M:%S", time.localtime(h["timestamp"]))
        print(f"  [{ts}] {h['id']} | {h['topic'][:25]:25s} | {h['status']:10s} | layer={h['source_layer']}")

    # 9. DLQ check
    print(f"\n[DLQ] Dead Letter Queue status:")
    dlq_stats = bus.dlq.stats()
    print(f"  Entries: {dlq_stats['total_entries']}/{dlq_stats['max_entries']}")
    if dlq_stats['topics']:
        print(f"  Topics in DLQ: {dlq_stats['topics']}")
    else:
        print(f"  DLQ is empty ✅")

    # 10. Cross-layer routing demo
    print(f"\n[CROSS-LAYER] Register cross-layer route Layer 11 -> Layer 12...")
    cross_log: List[str] = []
    def cross_handler(event: Event) -> None:
        cross_log.append(event.topic)
        print(f"  🔀 Cross-route: '{event.topic}' from L{event.source_layer}")

    cross_sub = bus.subscribe("ide.update", cross_handler, listen_from_layer=11, listen_to_layer=12)
    bus.publish("ide.update", {"file": "main.py", "change": "+42 lines"}, source_layer=11, target_layers=[12])
    time.sleep(0.3)
    print(f"  Cross-layer delivered: {len(cross_log)} event(s)")

    # 11. Wildcard matching demo
    print(f"\n[WILDCARD] Topic matching test:")
    test_topics = ["trading.btc.price", "trading.eth.price", "system.alert", "network.p2p.x"]
    for tt in test_topics:
        matches = bus.topic_router.match(tt)
        print(f"  '{tt}' -> matched {len(matches)} subscription(s)")

    # 12. Stop
    bus.stop()
    print(f"\n[STOP] Dispatcher halted")

    print(f"\n{'='*70}")
    print("  Demo complete. All events processed.")
    print(f"{'='*70}")
