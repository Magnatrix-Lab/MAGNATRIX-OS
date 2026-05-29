#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 4 — Kafka Native Client
Native Kafka-like protocol client (no confluent-kafka dependency).
- Message framing (length-prefixed, big-endian)
- Metadata request/response simulation
- Produce + Fetch API simulation
- Consumer group coordination (simple sync)
"""
import struct, json, time, threading, socket, hashlib, os, sys, random
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass


@dataclass
class KafkaMessage:
    topic: str
    partition: int
    key: bytes
    value: bytes
    offset: int = 0
    timestamp: int = 0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = int(time.time() * 1000)

    def to_bytes(self) -> bytes:
        key_len = len(self.key)
        val_len = len(self.value)
        header = struct.pack(">H", len(self.topic)) + self.topic.encode()
        header += struct.pack(">I", self.partition)
        header += struct.pack(">I", key_len) + self.key
        header += struct.pack(">I", val_len) + self.value
        header += struct.pack(">Q", self.timestamp)
        return struct.pack(">I", len(header)) + header

    @classmethod
    def from_bytes(cls, data: bytes) -> 'KafkaMessage':
        topic_len = struct.unpack(">H", data[:2])[0]
        topic = data[2:2 + topic_len].decode()
        offset = 2 + topic_len
        partition = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        key_len = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        key = data[offset:offset + key_len]
        offset += key_len
        val_len = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        value = data[offset:offset + val_len]
        offset += val_len
        timestamp = struct.unpack(">Q", data[offset:offset + 8])[0]
        return cls(topic, partition, key, value, timestamp=timestamp)


class KafkaProtocol:
    """Kafka-like wire protocol framing."""

    API_VERSION = 0

    @staticmethod
    def encode_request(api_key: int, correlation_id: int, payload: bytes) -> bytes:
        size = len(payload) + 6
        header = struct.pack(">I", size) + struct.pack(">H", api_key) + struct.pack(">H", KafkaProtocol.API_VERSION)
        header += struct.pack(">I", correlation_id)
        return header + payload

    @staticmethod
    def decode_response(data: bytes) -> Tuple[int, bytes]:
        if len(data) < 8:
            return -1, b""
        size = struct.unpack(">I", data[:4])[0]
        if len(data) < 4 + size:
            return -1, b""
        correlation_id = struct.unpack(">I", data[4:8])[0]
        payload = data[8:4 + size]
        return correlation_id, payload


class InMemoryLog:
    """In-memory topic log simulating Kafka partition log."""

    def __init__(self, topic: str, partition: int):
        self.topic = topic
        self.partition = partition
        self._messages: deque = deque(maxlen=100000)
        self._offset = 0
        self._lock = threading.Lock()

    def append(self, msg: KafkaMessage) -> int:
        with self._lock:
            msg.offset = self._offset
            msg.partition = self.partition
            self._messages.append(msg)
            self._offset += 1
            return msg.offset

    def read(self, start_offset: int, max_bytes: int = 1000000) -> List[KafkaMessage]:
        with self._lock:
            results = []
            total = 0
            for msg in self._messages:
                if msg.offset >= start_offset:
                    results.append(msg)
                    total += len(msg.value)
                    if total >= max_bytes:
                        break
            return results

    def high_watermark(self) -> int:
        with self._lock:
            return self._offset


class KafkaBroker:
    """Simulated Kafka broker with topic management."""

    def __init__(self, broker_id: int = 1):
        self.broker_id = broker_id
        self._topics: Dict[str, List[InMemoryLog]] = {}
        self._lock = threading.Lock()

    def create_topic(self, name: str, partitions: int = 3, replication: int = 1):
        with self._lock:
            if name not in self._topics:
                self._topics[name] = [InMemoryLog(name, i) for i in range(partitions)]

    def produce(self, topic: str, partition: int, key: bytes, value: bytes) -> int:
        with self._lock:
            if topic not in self._topics:
                self._topics[topic] = [InMemoryLog(topic, i) for i in range(3)]
            logs = self._topics[topic]
            if partition < 0 or partition >= len(logs):
                partition = hash(key) % len(logs) if key else random.randint(0, len(logs) - 1)
            msg = KafkaMessage(topic, partition, key, value)
            return logs[partition].append(msg)

    def fetch(self, topic: str, partition: int, offset: int, max_bytes: int = 1000000) -> List[KafkaMessage]:
        with self._lock:
            if topic not in self._topics:
                return []
            logs = self._topics[topic]
            if 0 <= partition < len(logs):
                return logs[partition].read(offset, max_bytes)
            return []

    def metadata(self, topics: List[str] = None) -> Dict:
        with self._lock:
            result = {}
            for name, logs in self._topics.items():
                if topics and name not in topics:
                    continue
                result[name] = {
                    "partitions": [
                        {"partition": i, "leader": self.broker_id, "replicas": [self.broker_id], "hwm": log.high_watermark()}
                        for i, log in enumerate(logs)
                    ]
                }
            return result


class ConsumerCoordinator:
    """Simple consumer group coordinator."""

    def __init__(self, group_id: str):
        self.group_id = group_id
        self._members: Dict[str, Dict[str, List[int]]] = {}  # member -> {topic: [partitions]}
        self._offsets: Dict[str, Dict[int, int]] = defaultdict(dict)
        self._lock = threading.Lock()

    def join(self, member_id: str, topics: List[str], partitions_per_topic: Dict[str, int]):
        with self._lock:
            # Simple range assignment
            assignment = {}
            members = list(self._members.keys()) + [member_id]
            for topic in topics:
                num_partitions = partitions_per_topic.get(topic, 3)
                all_partitions = list(range(num_partitions))
                for i, p in enumerate(all_partitions):
                    assigned_member = members[i % len(members)]
                    if assigned_member == member_id:
                        assignment.setdefault(topic, []).append(p)
            self._members[member_id] = assignment

    def leave(self, member_id: str):
        with self._lock:
            if member_id in self._members:
                del self._members[member_id]

    def commit(self, topic: str, partition: int, offset: int):
        with self._lock:
            self._offsets[f"{topic}:{partition}"] = offset

    def get_offset(self, topic: str, partition: int) -> int:
        with self._lock:
            return self._offsets.get(f"{topic}:{partition}", 0)


class NativeKafkaClient:
    """Full native Kafka client (simulated)."""

    def __init__(self, broker: KafkaBroker = None):
        self.broker = broker or KafkaBroker()
        self.coordinator: Optional[ConsumerCoordinator] = None

    def create_topic(self, name: str, partitions: int = 3):
        self.broker.create_topic(name, partitions)

    def produce(self, topic: str, value: bytes, key: bytes = b"", partition: int = -1) -> int:
        return self.broker.produce(topic, partition, key, value)

    def consume(self, topic: str, partition: int, offset: int = 0) -> List[KafkaMessage]:
        return self.broker.fetch(topic, partition, offset)

    def join_group(self, group_id: str, member_id: str, topics: List[str], partitions: Dict[str, int]):
        self.coordinator = ConsumerCoordinator(group_id)
        self.coordinator.join(member_id, topics, partitions)

    def commit(self, topic: str, partition: int, offset: int):
        if self.coordinator:
            self.coordinator.commit(topic, partition, offset)

    def metadata(self, topics: List[str] = None) -> Dict:
        return self.broker.metadata(topics)

    def stats(self) -> Dict:
        return {
            "broker_id": self.broker.broker_id,
            "topics": len(self.broker._topics),
            "coordinator": self.coordinator.group_id if self.coordinator else None,
        }


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("msg_serialize", lambda: (m := KafkaMessage("t", 0, b"k", b"v"), m2 := KafkaMessage.from_bytes(m.to_bytes()[4:]), m2.topic == "t" and m2.key == b"k")[2])
    _t("protocol_frame", lambda: (r := KafkaProtocol.encode_request(0, 1, b"x"), KafkaProtocol.decode_response(r)[0] == 1)[1])
    _t("log_append", lambda: (l := InMemoryLog("t", 0), l.append(KafkaMessage("t", 0, b"", b"v")) == 0)[1])
    _t("log_read", lambda: (l := InMemoryLog("t", 0), l.append(KafkaMessage("t", 0, b"", b"v")), len(l.read(0)) == 1)[1])
    _t("broker_produce_fetch", lambda: (b := KafkaBroker(), b.create_topic("t", 1), b.produce("t", 0, b"", b"hello"), len(b.fetch("t", 0, 0)) == 1)[3])
    _t("broker_metadata", lambda: (b := KafkaBroker(), b.create_topic("t", 2), "t" in b.metadata()))
    _t("coordinator_join", lambda: (c := ConsumerCoordinator("g1"), c.join("m1", ["t"], {"t": 3}), len(c._members["m1"].get("t", [])) > 0)[2])
    _t("coordinator_commit", lambda: (c := ConsumerCoordinator("g1"), c.commit("t", 0, 5), c.get_offset("t", 0) == 5)[2])
    _t("client_produce_consume", lambda: (cl := NativeKafkaClient(), cl.create_topic("t", 1), cl.produce("t", b"hello"), len(cl.consume("t", 0)) == 1)[3])
    _t("client_stats", lambda: "broker_id" in NativeKafkaClient().stats())

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nKafka Native: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
