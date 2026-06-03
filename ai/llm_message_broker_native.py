"""Message Broker - Pub/sub message broker for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable
from collections import deque

@dataclass
class MessageBroker:
    topics: Dict[str, deque] = field(default_factory=dict)
    subscribers: Dict[str, List[Callable]] = field(default_factory=dict)

    def create_topic(self, topic: str, max_size: int = 100) -> None:
        if topic not in self.topics:
            self.topics[topic] = deque(maxlen=max_size)
            self.subscribers[topic] = []

    def subscribe(self, topic: str, callback: Callable) -> None:
        self.create_topic(topic)
        self.subscribers[topic].append(callback)

    def publish(self, topic: str, message: str) -> None:
        self.create_topic(topic)
        self.topics[topic].append(message)
        for cb in self.subscribers[topic]:
            cb(message)

    def stats(self) -> dict:
        return {"topics": len(self.topics), "messages": sum(len(q) for q in self.topics.values())}

def run():
    mb = MessageBroker()
    received = []
    mb.subscribe("news", lambda m: received.append(m))
    mb.publish("news", "hello")
    print("Received:", received)
    print("Stats:", mb.stats())

if __name__ == "__main__": run()
