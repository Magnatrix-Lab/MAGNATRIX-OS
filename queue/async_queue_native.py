"""
async_queue_native.py — Native Async Message Queue
Pure Python stdlib. Priority queue, fan-out, persistent storage, TTL.
NativeAsyncQueue with run().
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class NativeAsyncQueue:
    """
    Native async message queue for inter-agent communication.

    Supports priority ordering, fan-out delivery, persistent storage,
    TTL (time-to-live), and subscriber callbacks. Pure stdlib.

    Attributes:
        queue: In-memory priority queue list.
        subscribers: Topic -> set of callback functions.
        persist_path: Optional file path for disk persistence.
        ttl_seconds: Default TTL for messages.
    """

    def __init__(
        self,
        persist_path: Optional[str] = None,
        ttl_seconds: float = 300.0,
    ) -> None:
        self.queue: List[Dict[str, Any]] = []
        self.subscribers: Dict[str, Set[Callable[[Dict[str, Any]], None]]] = defaultdict(set)
        self.lock = threading.RLock()
        self.persist_path = persist_path
        self.ttl_seconds = ttl_seconds
        self._seq = 0
        self._running = True
        self._gc_thread = threading.Thread(target=self._gc_loop, daemon=True)
        self._gc_thread.start()
        if self.persist_path and os.path.exists(self.persist_path):
            self._load()

    def _next_seq(self) -> int:
        with self.lock:
            self._seq += 1
            return self._seq

    def enqueue(
        self,
        topic: str,
        payload: Any,
        priority: int = 0,
        ttl: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Enqueue a message.

        Args:
            topic: Routing topic.
            payload: Message body (JSON-serializable).
            priority: Lower is higher priority.
            ttl: Seconds until expiry; default ttl_seconds if None.
            meta: Optional metadata dict.

        Returns:
            Message ID string.
        """
        msg_id = f"{topic}:{self._next_seq()}:{int(time.time() * 1000)}"
        msg = {
            "id": msg_id,
            "topic": topic,
            "payload": payload,
            "priority": priority,
            "created_at": time.time(),
            "ttl": ttl if ttl is not None else self.ttl_seconds,
            "meta": meta or {},
            "delivered_to": [],
            "attempts": 0,
        }
        with self.lock:
            self.queue.append(msg)
            # Re-sort by priority ascending, then created_at ascending
            self.queue.sort(key=lambda m: (m["priority"], m["created_at"]))
            self._persist()
        return msg_id

    def dequeue(self, topic: Optional[str] = None, max_items: int = 1) -> List[Dict[str, Any]]:
        """
        Dequeue messages. If topic is given, filter by topic.

        Args:
            topic: Optional topic filter.
            max_items: Max messages to return.

        Returns:
            List of message dicts (removed from queue).
        """
        now = time.time()
        results: List[Dict[str, Any]] = []
        with self.lock:
            remaining: List[Dict[str, Any]] = []
            for msg in self.queue:
                if len(results) < max_items:
                    if topic is None or msg["topic"] == topic:
                        if now - msg["created_at"] < msg["ttl"]:
                            msg["attempts"] += 1
                            results.append(msg)
                            continue
                remaining.append(msg)
            self.queue = remaining
            self._persist()
        return results

    def peek(self, topic: Optional[str] = None, max_items: int = 5) -> List[Dict[str, Any]]:
        """Peek at messages without removing them."""
        now = time.time()
        with self.lock:
            msgs = []
            for msg in self.queue:
                if len(msgs) >= max_items:
                    break
                if topic is None or msg["topic"] == topic:
                    if now - msg["created_at"] < msg["ttl"]:
                        msgs.append({k: v for k, v in msg.items() if k != "delivered_to"})
            return msgs

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe a callback to a topic for fan-out delivery."""
        with self.lock:
            self.subscribers[topic].add(callback)

    def unsubscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Remove a callback subscription."""
        with self.lock:
            self.subscribers[topic].discard(callback)

    def fanout(self, topic: str, payload: Any, priority: int = 0) -> int:
        """
        Enqueue and immediately deliver to all subscribers.

        Returns:
            Number of subscribers notified.
        """
        msg_id = self.enqueue(topic, payload, priority=priority)
        count = 0
        with self.lock:
            subs = list(self.subscribers.get(topic, set()))
        for cb in subs:
            try:
                cb({"id": msg_id, "topic": topic, "payload": payload})
                count += 1
            except Exception:
                pass
        return count

    def _gc_loop(self) -> None:
        """Background thread to purge expired messages."""
        while self._running:
            time.sleep(10)
            self._purge_expired()

    def _purge_expired(self) -> None:
        now = time.time()
        with self.lock:
            before = len(self.queue)
            self.queue = [m for m in self.queue if now - m["created_at"] < m["ttl"]]
            if len(self.queue) != before:
                self._persist()

    def _persist(self) -> None:
        if not self.persist_path:
            return
        try:
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(self.queue, f, indent=2)
        except Exception:
            pass

    def _load(self) -> None:
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                self.queue = json.load(f)
        except Exception:
            self.queue = []

    def stats(self) -> Dict[str, Any]:
        """Queue statistics."""
        with self.lock:
            topics: Dict[str, int] = {}
            for msg in self.queue:
                topics[msg["topic"]] = topics.get(msg["topic"], 0) + 1
            return {
                "total_messages": len(self.queue),
                "topics": topics,
                "subscribers": {k: len(v) for k, v in self.subscribers.items()},
            }

    def shutdown(self) -> None:
        """Graceful shutdown."""
        self._running = False
        self._gc_thread.join(timeout=2)

    def run(self) -> Dict[str, Any]:
        """
        Self-test demo.

        Returns:
            Dict with test results and final stats.
        """
        results: Dict[str, Any] = {"status": "ok", "tests": []}

        # Test 1: Enqueue / dequeue
        self.enqueue("agent.tasks", {"cmd": "ping"}, priority=1)
        self.enqueue("agent.tasks", {"cmd": "pong"}, priority=0)
        msgs = self.dequeue("agent.tasks", max_items=2)
        assert len(msgs) == 2, "Expected 2 messages"
        assert msgs[0]["payload"]["cmd"] == "pong", "Priority ordering failed"
        results["tests"].append({"name": "enqueue_dequeue_priority", "pass": True})

        # Test 2: TTL expiry
        self.enqueue("ttl.test", {"data": "old"}, ttl=0.01)
        time.sleep(0.05)
        expired = self.dequeue("ttl.test", max_items=1)
        assert len(expired) == 0, "Expired message should not be dequeued"
        results["tests"].append({"name": "ttl_expiry", "pass": True})

        # Test 3: Fan-out
        received: List[Dict[str, Any]] = []
        def cb(msg: Dict[str, Any]) -> None:
            received.append(msg)
        self.subscribe("alerts", cb)
        count = self.fanout("alerts", {"level": "warn"})
        assert count == 1, "Expected 1 subscriber notified"
        assert len(received) == 1, "Expected 1 received message"
        results["tests"].append({"name": "fanout", "pass": True})

        # Test 4: Persistence
        tmp_path = "/tmp/native_async_queue_test.json"
        q2 = NativeAsyncQueue(persist_path=tmp_path, ttl_seconds=60)
        q2.enqueue("persist", {"k": "v"})
        q3 = NativeAsyncQueue(persist_path=tmp_path, ttl_seconds=60)
        assert len(q3.dequeue("persist", max_items=1)) == 1, "Persistence load failed"
        os.remove(tmp_path)
        results["tests"].append({"name": "persistence", "pass": True})

        # Test 5: Thread safety
        errors: List[str] = []
        def worker():
            try:
                for _ in range(50):
                    self.enqueue("stress", {"x": 1})
                    self.dequeue("stress", max_items=1)
            except Exception as e:
                errors.append(str(e))
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        results["tests"].append({"name": "thread_safety", "pass": len(errors) == 0, "errors": errors})

        # Test 6: Stats
        stats = self.stats()
        assert "topics" in stats, "Stats missing topics"
        results["tests"].append({"name": "stats", "pass": True})

        results["summary"] = f"{sum(1 for t in results['tests'] if t['pass'])}/{len(results['tests'])} tests passed"
        results["final_stats"] = self.stats()
        return results


if __name__ == "__main__":
    queue = NativeAsyncQueue(persist_path="/tmp/native_async_queue_demo.json")
    try:
        print(queue.run())
    finally:
        queue.shutdown()
