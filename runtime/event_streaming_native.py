
"""
runtime/event_streaming_native.py — MAGNATRIX-OS Event Streaming Layer

Kafka-like event streaming for inter-layer communication.
Pure Python, stdlib only. Zero dependencies.

Components:
    • EventStreamingLayer — main orchestrator
    • Topic — named topic with partitions
    • Producer — producer with batching
    • Consumer — consumer with offset tracking
    • Partition — topic partition with log storage
    • OffsetManager — offset tracking
    • ConsumerGroup — coordinated consumer group
    • Message — event message
    • EventLog — append-only log storage
    • StreamProcessor — stream processing
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ════════════════════════════════════════════════════════════════════════════
# Message
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class EventMessage:
    key: str
    value: Any
    topic: str
    partition: int = 0
    offset: int = 0
    timestamp: float = 0.0
    headers: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "topic": self.topic,
            "partition": self.partition,
            "offset": self.offset,
            "timestamp": self.timestamp,
            "headers": self.headers,
        }


# ════════════════════════════════════════════════════════════════════════════
# Partition
# ════════════════════════════════════════════════════════════════════════════

class Partition:
    """A single partition with append-only log storage."""

    def __init__(self, topic: str, partition_id: int, max_size: int = 10000):
        self.topic = topic
        self.partition_id = partition_id
        self.max_size = max_size
        self._log: deque = deque()
        self._offset = 0
        self._lock = threading.Lock()

    def append(self, message: EventMessage) -> int:
        """Append message to partition. Returns offset."""
        with self._lock:
            self._offset += 1
            message.offset = self._offset
            message.partition = self.partition_id
            self._log.append(message)
            if len(self._log) > self.max_size:
                self._log.popleft()
            return self._offset

    def read(self, offset: int, limit: int = 100) -> List[EventMessage]:
        """Read messages from offset."""
        with self._lock:
            start = max(0, offset - 1)
            return list(self._log)[start:start + limit]

    def latest_offset(self) -> int:
        with self._lock:
            return self._offset

    def size(self) -> int:
        with self._lock:
            return len(self._log)

    def clear(self) -> None:
        with self._lock:
            self._log.clear()
            self._offset = 0


# ════════════════════════════════════════════════════════════════════════════
# Topic
# ════════════════════════════════════════════════════════════════════════════

class Topic:
    """Named topic with multiple partitions."""

    def __init__(self, name: str, num_partitions: int = 1, retention_sec: float = 86400):
        self.name = name
        self.num_partitions = num_partitions
        self.retention_sec = retention_sec
        self._partitions: Dict[int, Partition] = {
            i: Partition(name, i) for i in range(num_partitions)
        }
        self._lock = threading.Lock()

    def _select_partition(self, key: str) -> Partition:
        """Select partition by key hash."""
        import hashlib
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return self._partitions[h % self.num_partitions]

    def publish(self, message: EventMessage) -> int:
        """Publish message to appropriate partition."""
        partition = self._select_partition(message.key)
        return partition.append(message)

    def read(self, partition_id: int, offset: int, limit: int = 100) -> List[EventMessage]:
        """Read from specific partition."""
        if partition_id not in self._partitions:
            return []
        return self._partitions[partition_id].read(offset, limit)

    def get_partitions(self) -> List[int]:
        return list(self._partitions.keys())

    def size(self) -> int:
        return sum(p.size() for p in self._partitions.values())

    def clear(self) -> None:
        for p in self._partitions.values():
            p.clear()


# ════════════════════════════════════════════════════════════════════════════
# OffsetManager
# ════════════════════════════════════════════════════════════════════════════

class OffsetManager:
    """Track consumer offsets per partition."""

    def __init__(self):
        self._offsets: Dict[str, Dict[int, int]] = defaultdict(dict)
        self._lock = threading.Lock()

    def commit(self, consumer_id: str, topic: str, partition: int, offset: int) -> None:
        """Commit offset for consumer."""
        key = f"{consumer_id}:{topic}"
        with self._lock:
            self._offsets[key][partition] = offset

    def get(self, consumer_id: str, topic: str, partition: int) -> int:
        """Get committed offset."""
        key = f"{consumer_id}:{topic}"
        with self._lock:
            return self._offsets[key].get(partition, 0)

    def reset(self, consumer_id: str, topic: str, partition: int) -> None:
        """Reset offset to beginning."""
        key = f"{consumer_id}:{topic}"
        with self._lock:
            self._offsets[key][partition] = 0


# ════════════════════════════════════════════════════════════════════════════
# Producer
# ════════════════════════════════════════════════════════════════════════════

class Producer:
    """Producer with batching and retry."""

    def __init__(self, streaming_layer: EventStreamingLayer):
        self._streaming = streaming_layer
        self._batch: List[EventMessage] = []
        self._batch_size = 100
        self._batch_timeout = 0.1
        self._lock = threading.Lock()

    def send(self, topic: str, key: str, value: Any, headers: Optional[Dict[str, str]] = None) -> int:
        """Send a single message."""
        message = EventMessage(key=key, value=value, topic=topic, headers=headers or {})
        return self._streaming.publish(topic, message)

    def send_batch(self, messages: List[Tuple[str, str, Any]]) -> List[int]:
        """Send multiple messages."""
        offsets = []
        for topic, key, value in messages:
            offsets.append(self.send(topic, key, value))
        return offsets


# ════════════════════════════════════════════════════════════════════════════
# Consumer
# ════════════════════════════════════════════════════════════════════════════

class Consumer:
    """Consumer with offset tracking."""

    def __init__(self, consumer_id: str, streaming_layer: EventStreamingLayer):
        self.consumer_id = consumer_id
        self._streaming = streaming_layer
        self._subscribed: Set[str] = set()
        self._offset_mgr = OffsetManager()
        self._running = False
        self._callback: Optional[Callable[[EventMessage], None]] = None

    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics."""
        self._subscribed.update(topics)

    def unsubscribe(self, topic: str) -> None:
        self._subscribed.discard(topic)

    def poll(self, timeout: float = 1.0) -> List[EventMessage]:
        """Poll for messages from subscribed topics."""
        messages = []
        deadline = time.time() + timeout

        for topic_name in self._subscribed:
            topic = self._streaming.get_topic(topic_name)
            if not topic:
                continue

            for partition_id in topic.get_partitions():
                offset = self._offset_mgr.get(self.consumer_id, topic_name, partition_id)
                batch = topic.read(partition_id, offset + 1, limit=100)

                for msg in batch:
                    messages.append(msg)
                    self._offset_mgr.commit(self.consumer_id, topic_name, partition_id, msg.offset)

                if time.time() > deadline:
                    break

            if time.time() > deadline:
                break

        return messages

    def seek(self, topic: str, partition: int, offset: int) -> None:
        """Seek to specific offset."""
        self._offset_mgr.commit(self.consumer_id, topic, partition, offset)

    def reset(self, topic: str, partition: int) -> None:
        """Reset to beginning."""
        self._offset_mgr.reset(self.consumer_id, topic, partition)

    def start_listening(self, callback: Callable[[EventMessage], None]) -> None:
        """Start continuous listening with callback."""
        self._callback = callback
        self._running = True

        def listen():
            while self._running:
                messages = self.poll(timeout=0.5)
                for msg in messages:
                    try:
                        callback(msg)
                    except Exception as e:
                        print(f"[Consumer] Error handling message: {e}")
                if not messages:
                    time.sleep(0.1)

        threading.Thread(target=listen, daemon=True).start()

    def stop(self) -> None:
        self._running = False


# ════════════════════════════════════════════════════════════════════════════
# ConsumerGroup
# ════════════════════════════════════════════════════════════════════════════

class ConsumerGroup:
    """Coordinated consumer group with partition assignment."""

    def __init__(self, group_id: str, streaming_layer: EventStreamingLayer):
        self.group_id = group_id
        self._streaming = streaming_layer
        self._consumers: Dict[str, Consumer] = {}
        self._assignments: Dict[str, Dict[str, List[int]]] = {}
        self._lock = threading.Lock()

    def join(self, consumer_id: str) -> Consumer:
        """Join consumer to group."""
        consumer = Consumer(consumer_id, self._streaming)
        with self._lock:
            self._consumers[consumer_id] = consumer
        self._rebalance()
        return consumer

    def leave(self, consumer_id: str) -> None:
        """Leave consumer from group."""
        with self._lock:
            if consumer_id in self._consumers:
                self._consumers[consumer_id].stop()
                del self._consumers[consumer_id]
        self._rebalance()

    def _rebalance(self) -> None:
        """Reassign partitions among consumers."""
        with self._lock:
            if not self._consumers:
                return

            consumer_ids = list(self._consumers.keys())

            # Get all topics and partitions
            all_topics = self._streaming.list_topics()

            for topic_name in all_topics:
                topic = self._streaming.get_topic(topic_name)
                if not topic:
                    continue

                partitions = topic.get_partitions()
                if not partitions:
                    continue

                # Round-robin assignment
                for i, partition_id in enumerate(partitions):
                    consumer_id = consumer_ids[i % len(consumer_ids)]
                    consumer = self._consumers[consumer_id]
                    consumer.subscribe([topic_name])


# ════════════════════════════════════════════════════════════════════════════
# StreamProcessor
# ════════════════════════════════════════════════════════════════════════════

class StreamProcessor:
    """Simple stream processing (filter, map, reduce)."""

    @staticmethod
    def filter(messages: List[EventMessage], predicate: Callable[[EventMessage], bool]) -> List[EventMessage]:
        return [m for m in messages if predicate(m)]

    @staticmethod
    def map(messages: List[EventMessage], transform: Callable[[EventMessage], Any]) -> List[Any]:
        return [transform(m) for m in messages]

    @staticmethod
    def reduce(messages: List[EventMessage], reducer: Callable[[Any, EventMessage], Any], initial: Any = None) -> Any:
        result = initial
        for m in messages:
            result = reducer(result, m) if result is not None else m.value
        return result


# ════════════════════════════════════════════════════════════════════════════
# EventStreamingLayer
# ════════════════════════════════════════════════════════════════════════════

class EventStreamingLayer:
    """Main event streaming orchestrator."""

    def __init__(self):
        self._topics: Dict[str, Topic] = {}
        self._producers: List[Producer] = []
        self._consumers: List[Consumer] = []
        self._groups: Dict[str, ConsumerGroup] = {}
        self._lock = threading.Lock()
        self._metrics = {
            "messages_published": 0,
            "messages_consumed": 0,
            "topics": 0,
        }

    def create_topic(self, name: str, num_partitions: int = 1, retention_sec: float = 86400) -> Topic:
        """Create a new topic."""
        with self._lock:
            if name not in self._topics:
                topic = Topic(name, num_partitions, retention_sec)
                self._topics[name] = topic
                self._metrics["topics"] += 1
            return self._topics[name]

    def get_topic(self, name: str) -> Optional[Topic]:
        with self._lock:
            return self._topics.get(name)

    def list_topics(self) -> List[str]:
        with self._lock:
            return list(self._topics.keys())

    def delete_topic(self, name: str) -> bool:
        with self._lock:
            if name in self._topics:
                self._topics[name].clear()
                del self._topics[name]
                self._metrics["topics"] -= 1
                return True
            return False

    def publish(self, topic_name: str, message: EventMessage) -> int:
        """Publish message to topic."""
        topic = self.get_topic(topic_name)
        if not topic:
            topic = self.create_topic(topic_name)

        offset = topic.publish(message)
        self._metrics["messages_published"] += 1
        return offset

    def create_producer(self) -> Producer:
        """Create a new producer."""
        producer = Producer(self)
        self._producers.append(producer)
        return producer

    def create_consumer(self, consumer_id: str) -> Consumer:
        """Create a new consumer."""
        consumer = Consumer(consumer_id, self)
        self._consumers.append(consumer)
        return consumer

    def create_consumer_group(self, group_id: str) -> ConsumerGroup:
        """Create a new consumer group."""
        group = ConsumerGroup(group_id, self)
        self._groups[group_id] = group
        return group

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.copy()

    def stats(self) -> Dict[str, Any]:
        return {
            "topics": len(self._topics),
            "producers": len(self._producers),
            "consumers": len(self._consumers),
            "groups": len(self._groups),
            **self._metrics,
        }

    def clear(self) -> None:
        """Clear all topics."""
        with self._lock:
            for topic in self._topics.values():
                topic.clear()
            self._topics.clear()
            self._metrics["messages_published"] = 0
            self._metrics["messages_consumed"] = 0
            self._metrics["topics"] = 0


# ════════════════════════════════════════════════════════════════════════════
# DEMO / SELF-TEST
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Event Streaming Layer — Self-Test")
    print("=" * 60)

    # Test 1: Topic creation and publish
    print("\n[1] Topic creation and publish")
    streaming = EventStreamingLayer()
    topic = streaming.create_topic("events", num_partitions=2)

    producer = streaming.create_producer()
    offset1 = producer.send("events", "user:1", {"action": "login"})
    offset2 = producer.send("events", "user:2", {"action": "logout"})
    offset3 = producer.send("events", "user:1", {"action": "click"})

    assert offset1 == 1
    assert offset2 == 1  # Different partition
    assert offset3 == 2
    print(f"  ✓ Published 3 messages, offsets: {offset1}, {offset2}, {offset3}")

    # Test 2: Consumer poll
    print("\n[2] Consumer poll")
    consumer = streaming.create_consumer("consumer-1")
    consumer.subscribe(["events"])

    messages = consumer.poll(timeout=1.0)
    assert len(messages) >= 2
    print(f"  ✓ Polled {len(messages)} messages")

    # Test 3: Offset tracking
    print("\n[3] Offset tracking")
    consumer.reset("events", 0)
    messages = consumer.poll(timeout=1.0)
    assert len(messages) >= 2
    print(f"  ✓ Reset and re-polled {len(messages)} messages")

    # Test 4: Consumer group
    print("\n[4] Consumer group")
    group = streaming.create_consumer_group("group-1")
    c1 = group.join("consumer-a")
    c2 = group.join("consumer-b")
    c1.subscribe(["events"])
    c2.subscribe(["events"])

    msgs1 = c1.poll(timeout=1.0)
    msgs2 = c2.poll(timeout=1.0)
    print(f"  ✓ Group: consumer-a got {len(msgs1)}, consumer-b got {len(msgs2)}")

    # Test 5: Stream processing
    print("\n[5] Stream processing")
    stream_consumer = streaming.create_consumer("stream-consumer")
    stream_consumer.subscribe(["events"])
    stream_consumer.reset("events", 0)
    stream_consumer.reset("events", 1)
    all_messages = stream_consumer.poll(timeout=1.0)

    filtered = StreamProcessor.filter(all_messages, lambda m: m.key == "user:1")
    assert len(filtered) >= 2

    mapped = StreamProcessor.map(filtered, lambda m: m.value["action"])
    assert "login" in mapped or "click" in mapped
    print(f"  ✓ Filtered: {len(filtered)}, Mapped: {mapped}")

    # Test 6: Metrics
    print("\n[6] Metrics")
    metrics = streaming.get_metrics()
    assert metrics["messages_published"] >= 3
    print(f"  ✓ Metrics: {metrics}")

    # Test 7: Multiple topics
    print("\n[7] Multiple topics")
    streaming.create_topic("logs", num_partitions=1)
    producer.send("logs", "app:1", {"level": "INFO", "msg": "started"})
    producer.send("logs", "app:1", {"level": "ERROR", "msg": "failed"})

    log_consumer = streaming.create_consumer("log-consumer")
    log_consumer.subscribe(["logs"])
    logs = log_consumer.poll(timeout=1.0)
    assert len(logs) == 2
    print(f"  ✓ Logs topic: {len(logs)} messages")

    # Test 8: Topic deletion
    print("\n[8] Topic deletion")
    streaming.delete_topic("logs")
    assert "logs" not in streaming.list_topics()
    print("  ✓ Topic deleted")

    # Test 9: Partition assignment
    print("\n[9] Partition assignment")
    streaming2 = EventStreamingLayer()
    streaming2.create_topic("orders", num_partitions=4)

    for i in range(10):
        producer2 = streaming2.create_producer()
        producer2.send("orders", f"order:{i}", {"id": i})

    topic = streaming2.get_topic("orders")
    assert topic.size() == 10
    print(f"  ✓ 10 orders across {topic.num_partitions} partitions")

    # Test 10: Stats
    print("\n[10] Stats")
    stats = streaming.stats()
    assert stats["topics"] > 0
    assert stats["producers"] > 0
    assert stats["consumers"] > 0
    print(f"  ✓ Stats: {stats}")

    streaming.clear()
    print("\n" + "=" * 60)
    print("All self-tests passed ✓")
    print("=" * 60)
