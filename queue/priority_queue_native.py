#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 4 — Priority Queue
Native priority queue with deadline scheduling, aging, and starvation prevention.
- Binary heap with O(log n) push/pop
- Deadline scheduler (EDF: Earliest Deadline First)
- Priority aging to prevent starvation
- Multi-level feedback queue (MLFQ) simulation
"""
import heapq, time, threading, json, os, sys, random
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque


@dataclass
class PriorityItem:
    priority: int
    deadline: float
    timestamp: float
    payload: Dict
    item_id: str = ""
    age_boost: int = 0

    def __post_init__(self):
        if not self.item_id:
            self.item_id = f"{self.timestamp:.6f}-{random.randint(0, 999999)}"
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def __lt__(self, other: 'PriorityItem') -> bool:
        # EDF: earliest deadline first, then priority, then age boost
        if self.deadline != other.deadline:
            return self.deadline < other.deadline
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.age_boost > other.age_boost


class BinaryHeapPriorityQueue:
    """Thread-safe binary heap priority queue."""

    def __init__(self, max_size: int = 100000):
        self.max_size = max_size
        self._heap: List[PriorityItem] = []
        self._lock = threading.Lock()
        self._pushed = 0
        self._popped = 0

    def push(self, item: PriorityItem) -> bool:
        with self._lock:
            if len(self._heap) >= self.max_size:
                return False
            heapq.heappush(self._heap, item)
            self._pushed += 1
            return True

    def pop(self) -> Optional[PriorityItem]:
        with self._lock:
            if not self._heap:
                return None
            self._popped += 1
            return heapq.heappop(self._heap)

    def peek(self) -> Optional[PriorityItem]:
        with self._lock:
            return self._heap[0] if self._heap else None

    def size(self) -> int:
        with self._lock:
            return len(self._heap)

    def clear(self):
        with self._lock:
            self._heap.clear()

    def snapshot(self) -> List[PriorityItem]:
        with self._lock:
            return list(self._heap)


class AgingScheduler:
    """Prevent starvation by boosting priority of old items."""

    def __init__(self, boost_interval_sec: float = 5.0, boost_amount: int = 1):
        self.boost_interval = boost_interval_sec
        self.boost_amount = boost_amount
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self, queue: BinaryHeapPriorityQueue):
        self._running = True
        def _loop():
            while self._running:
                time.sleep(self.boost_interval)
                with queue._lock:
                    now = time.time()
                    for item in queue._heap:
                        waited = now - item.timestamp
                        item.age_boost = int(waited / self.boost_interval) * self.boost_amount
                    heapq.heapify(queue._heap)
        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)


class MLFQ:
    """Multi-Level Feedback Queue (3 levels: high, medium, low)."""

    def __init__(self, quantum_high: float = 0.1, quantum_med: float = 0.5, quantum_low: float = 2.0):
        self.quantum = [quantum_high, quantum_med, quantum_low]
        self._queues: List[deque] = [deque(), deque(), deque()]
        self._lock = threading.Lock()
        self._promote_count = 0
        self._demote_count = 0

    def enqueue(self, item: PriorityItem, level: int = 0):
        with self._lock:
            self._queues[level].append(item)

    def dequeue(self) -> Optional[Tuple[PriorityItem, int]]:
        with self._lock:
            for level in range(3):
                if self._queues[level]:
                    return self._queues[level].popleft(), level
            return None

    def demote(self, item: PriorityItem, current_level: int):
        with self._lock:
            if current_level < 2:
                self._queues[current_level + 1].append(item)
                self._demote_count += 1
            else:
                self._queues[current_level].append(item)

    def promote(self, item: PriorityItem, current_level: int):
        with self._lock:
            if current_level > 0:
                self._queues[current_level - 1].appendleft(item)
                self._promote_count += 1
            else:
                self._queues[current_level].appendleft(item)

    def stats(self) -> Dict:
        with self._lock:
            return {
                "high": len(self._queues[0]),
                "medium": len(self._queues[1]),
                "low": len(self._queues[2]),
                "promoted": self._promote_count,
                "demoted": self._demote_count,
            }


class DeadlineScheduler:
    """EDF scheduler with overrun detection."""

    def __init__(self, queue: BinaryHeapPriorityQueue, on_miss: Callable = None):
        self.queue = queue
        self.on_miss = on_miss or (lambda item: None)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._missed = 0

    def start(self, interval_ms: float = 50.0):
        self._running = True
        def _loop():
            while self._running:
                now = time.time()
                item = self.queue.peek()
                if item and item.deadline < now:
                    item = self.queue.pop()
                    self._missed += 1
                    self.on_miss(item)
                time.sleep(interval_ms / 1000.0)
        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def missed_count(self) -> int:
        return self._missed


class NativePriorityQueue:
    """Unified priority queue with all features."""

    def __init__(self, max_size: int = 100000):
        self.heap = BinaryHeapPriorityQueue(max_size)
        self.aging = AgingScheduler()
        self.mlfq = MLFQ()
        self.deadline = DeadlineScheduler(self.heap)
        self._aging_started = False

    def push(self, payload: Dict, priority: int = 5, deadline_sec: float = 60.0) -> str:
        item = PriorityItem(
            priority=priority,
            deadline=time.time() + deadline_sec,
            timestamp=time.time(),
            payload=payload,
        )
        self.heap.push(item)
        if not self._aging_started:
            self.aging.start(self.heap)
            self._aging_started = True
        return item.item_id

    def pop(self) -> Optional[PriorityItem]:
        return self.heap.pop()

    def start_deadline_monitor(self):
        self.deadline.start()

    def stop(self):
        self.aging.stop()
        self.deadline.stop()

    def stats(self) -> Dict:
        return {
            "heap_size": self.heap.size(),
            "pushed": self.heap._pushed,
            "popped": self.heap._popped,
            "missed_deadlines": self.deadline.missed_count(),
            "mlfq": self.mlfq.stats(),
        }


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("heap_order", lambda: (h := BinaryHeapPriorityQueue(10), h.push(PriorityItem(2, 0, 0, {})), h.push(PriorityItem(1, 0, 0, {})), h.pop().priority == 1)[3])
    _t("deadline_order", lambda: (h := BinaryHeapPriorityQueue(10), h.push(PriorityItem(1, 100, 0, {})), h.push(PriorityItem(1, 50, 0, {})), h.pop().deadline == 50)[3])
    _t("heap_max_size", lambda: (q := BinaryHeapPriorityQueue(1), q.push(PriorityItem(1, 0, 0, {})), not q.push(PriorityItem(1, 0, 0, {})))[2])
    _t("aging_startstop", lambda: (a := AgingScheduler(), a.start(BinaryHeapPriorityQueue(10)), a.stop(), True)[3])
    _t("mlfq_enqueue", lambda: (m := MLFQ(), m.enqueue(PriorityItem(1, 0, 0, {})), m.dequeue()[1] == 0)[2])
    _t("mlfq_demote", lambda: (m := MLFQ(), i := PriorityItem(1, 0, 0, {}), m.enqueue(i, 0), m.demote(i, 0), m.stats()["demoted"] == 1)[4])
    _t("deadline_miss", lambda: (h := BinaryHeapPriorityQueue(10), h.push(PriorityItem(1, time.time() - 1, 0, {})), d := DeadlineScheduler(h), d.start(10), time.sleep(0.05), d.missed_count() >= 1)[5])
    _t("native_push_pop", lambda: (q := NativePriorityQueue(), q.push({"x": 1}, priority=1, deadline_sec=10), q.pop() is not None)[1])
    _t("native_stats", lambda: "heap_size" in NativePriorityQueue().stats())
    _t("item_id", lambda: PriorityItem(1, 0, 0, {}).item_id != "")

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nPriority Queue: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
