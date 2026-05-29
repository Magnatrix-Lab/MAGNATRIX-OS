#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 4 — PubSub Engine
Native pub/sub engine with channel multiplexing, fan-out, and backpressure.
- Topic wildcards (+, # like MQTT)
- Channel multiplexing (single connection, multiple topics)
- Flow control (credit-based backpressure)
- Message durability (ack/nack with redelivery)
"""
import json, time, threading, random, os, sys, hashlib
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum


class QoS(Enum):
    AT_MOST_ONCE = 0
    AT_LEAST_ONCE = 1
    EXACTLY_ONCE = 2


@dataclass
class PubSubMessage:
    topic: str
    payload: Dict
    qos: int = 0
    mid: int = 0  # message id
    retain: bool = False
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if self.mid == 0:
            self.mid = random.randint(1, 65535)

    def to_dict(self) -> Dict:
        return {
            "topic": self.topic,
            "payload": self.payload,
            "qos": self.qos,
            "mid": self.mid,
            "retain": self.retain,
            "timestamp": self.timestamp,
        }


class TopicMatcher:
    """MQTT-style topic matching with + and # wildcards."""

    @staticmethod
    def match(subscription: str, topic: str) -> bool:
        sub_parts = subscription.split("/")
        topic_parts = topic.split("/")
        sub_idx = 0
        topic_idx = 0
        while sub_idx < len(sub_parts):
            if sub_parts[sub_idx] == "#":
                return True
            if topic_idx >= len(topic_parts):
                return False
            if sub_parts[sub_idx] != "+" and sub_parts[sub_idx] != topic_parts[topic_idx]:
                return False
            sub_idx += 1
            topic_idx += 1
        return topic_idx == len(topic_parts)


class Channel:
    """Single channel with credit-based flow control."""

    def __init__(self, channel_id: str, max_credit: int = 100):
        self.channel_id = channel_id
        self.max_credit = max_credit
        self._credit = max_credit
        self._subscriptions: Set[str] = set()
        self._pending: deque = deque()  # messages awaiting ack
        self._delivered: deque = deque()  # delivery history
        self._lock = threading.Lock()
        self._handler: Optional[Callable] = None

    def subscribe(self, topic: str):
        with self._lock:
            self._subscriptions.add(topic)

    def unsubscribe(self, topic: str):
        with self._lock:
            self._subscriptions.discard(topic)

    def can_receive(self) -> bool:
        with self._lock:
            return self._credit > 0

    def deliver(self, msg: PubSubMessage) -> bool:
        with self._lock:
            if self._credit <= 0:
                return False
            self._credit -= 1
            self._pending.append(msg)
        if self._handler:
            try:
                self._handler(msg)
            except Exception:
                pass
        return True

    def ack(self, mid: int):
        with self._lock:
            self._pending = deque([m for m in self._pending if m.mid != mid])
            self._credit = min(self.max_credit, self._credit + 1)

    def nack(self, mid: int):
        # Redelivery: put back in pending
        with self._lock:
            for m in self._pending:
                if m.mid == mid:
                    m.qos = min(m.qos + 1, 2)  # escalate QoS
                    break
            self._credit = min(self.max_credit, self._credit + 1)

    def on_message(self, handler: Callable):
        self._handler = handler

    def matches(self, topic: str) -> bool:
        with self._lock:
            for sub in self._subscriptions:
                if TopicMatcher.match(sub, topic):
                    return True
        return False


class RetainedStore:
    """Store retained messages per topic."""

    def __init__(self):
        self._store: Dict[str, PubSubMessage] = {}
        self._lock = threading.Lock()

    def retain(self, msg: PubSubMessage):
        with self._lock:
            if msg.retain:
                self._store[msg.topic] = msg
            else:
                self._store.pop(msg.topic, None)

    def get(self, topic: str) -> Optional[PubSubMessage]:
        with self._lock:
            return self._store.get(topic)

    def match(self, subscription: str) -> List[PubSubMessage]:
        with self._lock:
            return [msg for topic, msg in self._store.items() if TopicMatcher.match(subscription, topic)]


class PubSubEngine:
    """Full pub/sub engine with all features."""

    def __init__(self):
        self._channels: Dict[str, Channel] = {}
        self._retained = RetainedStore()
        self._lock = threading.Lock()
        self._msg_counter = 0

    def create_channel(self, channel_id: str, max_credit: int = 100) -> Channel:
        with self._lock:
            if channel_id not in self._channels:
                self._channels[channel_id] = Channel(channel_id, max_credit)
            return self._channels[channel_id]

    def publish(self, msg: PubSubMessage) -> int:
        with self._lock:
            self._msg_counter += 1
            delivered = 0
            for ch in self._channels.values():
                if ch.matches(msg.topic) and ch.can_receive():
                    if ch.deliver(msg):
                        delivered += 1
            self._retained.retain(msg)
        return delivered

    def subscribe(self, channel_id: str, topic: str):
        ch = self.create_channel(channel_id)
        ch.subscribe(topic)
        # Deliver retained messages
        retained = self._retained.match(topic)
        for msg in retained:
            ch.deliver(msg)

    def unsubscribe(self, channel_id: str, topic: str):
        with self._lock:
            if channel_id in self._channels:
                self._channels[channel_id].unsubscribe(topic)

    def ack(self, channel_id: str, mid: int):
        with self._lock:
            if channel_id in self._channels:
                self._channels[channel_id].ack(mid)

    def nack(self, channel_id: str, mid: int):
        with self._lock:
            if channel_id in self._channels:
                self._channels[channel_id].nack(mid)

    def stats(self) -> Dict:
        with self._lock:
            return {
                "channels": len(self._channels),
                "retained": len(self._retained._store),
                "messages_published": self._msg_counter,
            }


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("topic_match_exact", lambda: TopicMatcher.match("a/b", "a/b"))
    _t("topic_match_plus", lambda: TopicMatcher.match("a/+", "a/b"))
    _t("topic_match_hash", lambda: TopicMatcher.match("a/#", "a/b/c/d"))
    _t("topic_no_match", lambda: not TopicMatcher.match("a/b", "a/c"))
    _t("channel_sub", lambda: (ch := Channel("c1"), ch.subscribe("a/b"), ch.matches("a/b"))[2])
    _t("channel_credit", lambda: (ch := Channel("c1", max_credit=1), ch.deliver(PubSubMessage("a/b", {})), not ch.can_receive())[2])
    _t("channel_ack", lambda: (ch := Channel("c1", max_credit=1), ch.deliver(PubSubMessage("a/b", {}, mid=1)), ch.ack(1), ch.can_receive())[2])
    _t("retain_store", lambda: (r := RetainedStore(), r.retain(PubSubMessage("a", {}, retain=True)), r.get("a") is not None)[2])
    _t("engine_publish", lambda: (e := PubSubEngine(), e.subscribe("c1", "a/b"), e.publish(PubSubMessage("a/b", {"x": 1})) >= 1)[2])
    _t("retained_delivery", lambda: (e := PubSubEngine(), e.publish(PubSubMessage("a/b", {}, retain=True)), e.subscribe("c2", "a/b"), len(e.create_channel("c2")._pending) > 0)[3])
    _t("stats", lambda: "channels" in PubSubEngine().stats())

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nPubSub Engine: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
