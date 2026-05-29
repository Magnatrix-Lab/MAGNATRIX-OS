"""
event_stream_native.py — Native Event Streaming Backbone
Pure Python stdlib. Pub/sub, topics, partitions, consumer groups,
at-least-once delivery. NativeEventStream with run().
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict, deque
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class NativeEventStream:
    """
    Native event streaming backbone.

    Simulates pub/sub with topics, partitions, consumer groups,
    and at-least-once delivery semantics. Pure stdlib.

    Attributes:
        topics: name -> list of partition deques.
        partitions: number of partitions per topic.
        subscribers: topic -> set of (group_id, callback).
        consumer_offsets: (group_id, topic, partition) -> last read index.
        committed: Dict of committed offsets for durability.
    """

    def __init__(
        self,
        partitions: int = 4,
        persist_path: Optional[str] = None,
    ) -> None:
        self.topics: Dict[str, List[deque]] = {}
        self.partitions = max(1, partitions)
        self.subscribers: Dict[str, Any] = defaultdict(set)
        self.lock = threading.RLock()
        self.consumer_offsets: Dict[Tuple[str, str, int], int] = {}
        self.committed_offsets: Dict[Tuple[str, str, int], int] = {}
        self.persist_path = persist_path
        self._seq = 0
        if self.persist_path and os.path.exists(self.persist_path):
            self._load()

    def _hash_partition(self, key: str) -> int:
        """Hash a key to a partition index."""
        return hash(key) % self.partitions

    def _next_seq(self) -> int:
        with self.lock:
            self._seq += 1
            return self._seq

    def create_topic(self, name: str) -> None:
        """Create a topic with N partitions."""
        with self.lock:
            if name not in self.topics:
                self.topics[name] = [deque() for _ in range(self.partitions)]

    def publish(
        self,
        topic: str,
        payload: Any,
        key: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Publish an event to a topic.

        Args:
            topic: Topic name.
            payload: Event body.
            key: Partition key; if None, round-robin.
            meta: Optional metadata.

        Returns:
            Event ID.
        """
        with self.lock:
            if topic not in self.topics:
                self.create_topic(topic)
            partition = self._hash_partition(key) if key else (self._seq % self.partitions)
            partition = partition % self.partitions
            event_id = f"{topic}:{partition}:{self._next_seq()}:{int(time.time() * 1000)}"
            event = {
                "id": event_id,
                "topic": topic,
                "partition": partition,
                "payload": payload,
                "meta": meta or {},
                "timestamp": time.time(),
                "delivered": [],
                "attempts": 0,
            }
            self.topics[topic][partition].append(event)
            self._persist()
        return event_id

    def subscribe(
        self,
        topic: str,
        group_id: str,
        callback: Callable[[Dict[str, Any]], bool],
    ) -> None:
        """
        Subscribe a consumer group callback to a topic.

        Args:
            topic: Topic name.
            group_id: Consumer group identifier.
            callback: Function receiving event dict, returns True if acked.
        """
        with self.lock:
            self.subscribers[topic].add((group_id, callback))

    def unsubscribe(
        self,
        topic: str,
        group_id: str,
        callback: Callable[[Dict[str, Any]], bool],
    ) -> None:
        """Remove a subscription."""
        with self.lock:
            self.subscribers[topic].discard((group_id, callback))

    def poll(
        self,
        topic: str,
        group_id: str,
        max_events: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Poll events for a consumer group from all partitions.

        Implements at-least-once delivery: event remains in queue
        until commit_offset is called.

        Args:
            topic: Topic name.
            group_id: Consumer group ID.
            max_events: Max events to return.

        Returns:
            List of event dicts.
        """
        results: List[Dict[str, Any]] = []
        with self.lock:
            if topic not in self.topics:
                return results
            for partition_idx, partition in enumerate(self.topics[topic]):
                offset_key = (group_id, topic, partition_idx)
                # Use committed offset as the base for at-least-once semantics
                offset = self.committed_offsets.get(offset_key, -1)
                for event in list(partition):
                    event_idx = list(partition).index(event)
                    if event_idx <= offset:
                        continue
                    if len(results) >= max_events:
                        break
                    event["attempts"] += 1
                    results.append(event)
                    # Update transient offset (not committed)
                    self.consumer_offsets[offset_key] = event_idx
                if len(results) >= max_events:
                    break
        return results

    def commit_offset(self, topic: str, group_id: str, partition: int, offset: int) -> None:
        """
        Commit offset for a consumer group, marking events as processed.

        Args:
            topic: Topic name.
            group_id: Consumer group.
            partition: Partition index.
            offset: Last successfully processed index.
        """
        key = (group_id, topic, partition)
        with self.lock:
            self.committed_offsets[key] = offset
            self._persist()

    def get_committed(self, topic: str, group_id: str, partition: int) -> int:
        """Get committed offset for a consumer group."""
        key = (group_id, topic, partition)
        with self.lock:
            return self.committed_offsets.get(key, -1)

    def fanout(self, topic: str, payload: Any, key: Optional[str] = None) -> int:
        """
        Publish and immediately deliver to all subscribers.

        Returns:
            Number of successful acks.
        """
        event_id = self.publish(topic, payload, key)
        count = 0
        with self.lock:
            subs = list(self.subscribers.get(topic, set()))
        for group_id, callback in subs:
            try:
                ack = callback({"id": event_id, "topic": topic, "payload": payload})
                if ack:
                    count += 1
            except Exception:
                pass
        return count

    def _persist(self) -> None:
        if not self.persist_path:
            return
        try:
            data = {
                "topics": {k: [list(p) for p in v] for k, v in self.topics.items()},
                "committed_offsets": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in self.committed_offsets.items()},
            }
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load(self) -> None:
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for topic, partitions in data.get("topics", {}).items():
                self.topics[topic] = [deque(p) for p in partitions]
            for k, v in data.get("committed_offsets", {}).items():
                parts = k.split("|")
                if len(parts) == 3:
                    self.committed_offsets[(parts[0], parts[1], int(parts[2]))] = v
        except Exception:
            pass

    def topic_stats(self, topic: str) -> Dict[str, Any]:
        """Return per-partition stats for a topic."""
        with self.lock:
            if topic not in self.topics:
                return {"exists": False}
            partitions = []
            for idx, part in enumerate(self.topics[topic]):
                partitions.append({
                    "partition": idx,
                    "messages": len(part),
                    "committed_offsets": {
                        g: self.committed_offsets.get((g, topic, idx), -1)
                        for g in set(s[0] for s in self.subscribers.get(topic, set()))
                    },
                })
            return {
                "exists": True,
                "partitions": self.partitions,
                "partition_stats": partitions,
                "subscribers": len(self.subscribers.get(topic, set())),
            }

    def run(self) -> Dict[str, Any]:
        """
        Self-test demo.

        Returns:
            Dict with test results and topic stats.
        """
        results: Dict[str, Any] = {"status": "ok", "tests": []}

        # Test 1: Publish / partition
        self.create_topic("events")
        e1 = self.publish("events", {"msg": "hello"}, key="user-1")
        e2 = self.publish("events", {"msg": "world"}, key="user-2")
        e3 = self.publish("events", {"msg": "again"}, key="user-1")
        assert e1.startswith("events:"), "Event ID format wrong"
        stats = self.topic_stats("events")
        assert stats["exists"] is True, "Topic should exist"
        total_msgs = sum(p["messages"] for p in stats["partition_stats"])
        assert total_msgs == 3, f"Expected 3 messages, got {total_msgs}"
        results["tests"].append({"name": "publish_partition", "pass": True})

        # Test 2: Poll / at-least-once
        self.create_topic("orders")
        for i in range(5):
            self.publish("orders", {"order_id": i}, key=f"order-{i}")
        msgs = self.poll("orders", "group-a", max_events=3)
        assert len(msgs) == 3, f"Expected 3 messages, got {len(msgs)}"
        # Re-poll without commit should give same messages again (at-least-once)
        msgs2 = self.poll("orders", "group-a", max_events=3)
        assert len(msgs2) == 3, f"Expected 3 messages again, got {len(msgs2)}"
        results["tests"].append({"name": "at_least_once", "pass": True})

        # Test 3: Commit offset
        self.commit_offset("orders", "group-a", msgs[0]["partition"], 0)
        self.commit_offset("orders", "group-a", msgs[0]["partition"], 1)
        committed = self.get_committed("orders", "group-a", msgs[0]["partition"])
        assert committed == 1, f"Expected committed=1, got {committed}"
        results["tests"].append({"name": "commit_offset", "pass": True})

        # Test 4: Consumer groups
        self.create_topic("logs")
        for i in range(4):
            self.publish("logs", {"log": i})
        msgs_g1 = self.poll("logs", "group-1", max_events=10)
        msgs_g2 = self.poll("logs", "group-2", max_events=10)
        assert len(msgs_g1) == 4, f"Group-1 expected 4, got {len(msgs_g1)}"
        assert len(msgs_g2) == 4, f"Group-2 expected 4, got {len(msgs_g2)}"
        results["tests"].append({"name": "consumer_groups", "pass": True})

        # Test 5: Fanout
        received: List[Dict[str, Any]] = []
        def ack_cb(msg: Dict[str, Any]) -> bool:
            received.append(msg)
            return True
        self.subscribe("alerts", "group-fan", ack_cb)
        count = self.fanout("alerts", {"level": "critical"})
        assert count == 1, f"Expected 1 ack, got {count}"
        assert len(received) == 1, f"Expected 1 received, got {len(received)}"
        results["tests"].append({"name": "fanout", "pass": True})

        # Test 6: Persistence
        tmp_path = "/tmp/native_event_stream_test.json"
        es2 = NativeEventStream(partitions=2, persist_path=tmp_path)
        es2.create_topic("persist")
        es2.publish("persist", {"k": "v"})
        es2.commit_offset("persist", "g1", 0, 0)
        es3 = NativeEventStream(partitions=2, persist_path=tmp_path)
        assert es3.get_committed("persist", "g1", 0) == 0, "Persistence load failed"
        os.remove(tmp_path)
        results["tests"].append({"name": "persistence", "pass": True})

        # Test 7: Thread safety
        errors: List[str] = []
        def worker():
            try:
                for i in range(50):
                    self.publish("stress", {"n": i})
                    self.poll("stress", f"g-{i}", max_events=1)
            except Exception as e:
                errors.append(str(e))
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        results["tests"].append({"name": "thread_safety", "pass": len(errors) == 0, "errors": errors})

        results["summary"] = f"{sum(1 for t in results['tests'] if t['pass'])}/{len(results['tests'])} tests passed"
        results["topic_stats"] = self.topic_stats("events")
        return results


if __name__ == "__main__":
    stream = NativeEventStream(partitions=4)
    print(stream.run())
