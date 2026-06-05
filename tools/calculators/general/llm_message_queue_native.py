"""Message Queue — pub/sub, topics, routing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, Any
from queue import Queue, Empty
from threading import Lock
import time
import uuid

@dataclass
class Message:
    msg_id: str
    topic: str
    payload: Any
    headers: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class MessageQueue:
    def __init__(self):
        self.topics: Dict[str, Queue] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        self.messages: Dict[str, Message] = {}
        self.lock = Lock()
        self.stats_history: List[Dict] = []

    def create_topic(self, topic: str):
        if topic not in self.topics:
            self.topics[topic] = Queue()
            self.subscribers[topic] = []

    def publish(self, topic: str, payload: Any, headers: Dict = None) -> str:
        self.create_topic(topic)
        msg_id = str(uuid.uuid4())[:8]
        msg = Message(msg_id, topic, payload, headers or {})
        self.topics[topic].put(msg)
        self.messages[msg_id] = msg
        with self.lock:
            for callback in self.subscribers[topic]:
                try:
                    callback(msg)
                except:
                    pass
        return msg_id

    def subscribe(self, topic: str, callback: Callable):
        self.create_topic(topic)
        with self.lock:
            self.subscribers[topic].append(callback)

    def consume(self, topic: str, timeout: Optional[float] = None) -> Optional[Message]:
        self.create_topic(topic)
        try:
            return self.topics[topic].get(timeout=timeout)
        except Empty:
            return None

    def get_topic_depth(self, topic: str) -> int:
        return self.topics[topic].qsize() if topic in self.topics else 0

    def stats(self) -> Dict:
        return {"topics": len(self.topics), "total_messages": len(self.messages), "depths": {t: q.qsize() for t, q in self.topics.items()}}

def run():
    mq = MessageQueue()
    received = []
    def handler(msg):
        received.append(msg.payload)
    mq.subscribe("orders", handler)
    mq.publish("orders", {"id": 1, "item": "book"})
    mq.publish("orders", {"id": 2, "item": "pen"})
    msg = mq.consume("orders", timeout=1)
    print(msg.payload if msg else None)
    print(received)
    print(mq.stats())

if __name__ == "__main__":
    run()
