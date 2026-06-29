"""
message_queue_engine_native.py
MAGNATRIX-OS — Message Queue Engine

Inspired by donnemartin/system-design-primer message queues:
Pub/sub, async processing, backpressure, delivery guarantees. Pure stdlib.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class Message:
    msg_id: str
    topic: str
    payload: Any
    priority: int = 0
    created_at: float = 0.0
    delivered: bool = False
    delivery_count: int = 0

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


class MessageQueueEngine:
    """Message queue engine with pub/sub, backpressure, and delivery tracking."""

    def __init__(self, data_dir: str = "./msg_queue", max_queue_size: int = 10000):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.queues: Dict[str, List[Message]] = {}
        self.subscribers: Dict[str, List[str]] = {}
        self.max_queue_size = max_queue_size
        self._load()

    def _load(self) -> None:
        for fname in ["queues.json", "subscribers.json"]:
            f = self.data_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "queues.json":
                            self.queues = {k: [Message(**m) for m in v] for k, v in data.items()}
                        else:
                            self.subscribers = data
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.data_dir / "queues.json", "w", encoding="utf-8") as f:
            json.dump({k: [asdict(m) for m in v] for k, v in self.queues.items()}, f, indent=2)
        with open(self.data_dir / "subscribers.json", "w", encoding="utf-8") as f:
            json.dump(self.subscribers, f, indent=2)

    def create_topic(self, topic: str) -> None:
        if topic not in self.queues:
            self.queues[topic] = []
            self.subscribers[topic] = []
            self._save()

    def subscribe(self, topic: str, subscriber_id: str) -> bool:
        self.create_topic(topic)
        if subscriber_id not in self.subscribers[topic]:
            self.subscribers[topic].append(subscriber_id)
            self._save()
            return True
        return False

    def publish(self, topic: str, msg_id: str, payload: Any, priority: int = 0) -> Optional[Message]:
        self.create_topic(topic)
        if len(self.queues[topic]) >= self.max_queue_size:
            return None  # Backpressure
        msg = Message(msg_id=msg_id, topic=topic, payload=payload, priority=priority)
        self.queues[topic].append(msg)
        self._save()
        return msg

    def consume(self, topic: str) -> Optional[Message]:
        if topic not in self.queues or not self.queues[topic]:
            return None
        # Priority ordering
        msg = min(self.queues[topic], key=lambda m: m.priority)
        self.queues[topic].remove(msg)
        msg.delivered = True
        msg.delivery_count += 1
        self._save()
        return msg

    def get_backpressure(self, topic: str) -> float:
        if topic not in self.queues:
            return 0.0
        return len(self.queues[topic]) / self.max_queue_size

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(v) for v in self.queues.values())
        topics = len(self.queues)
        return {"total_messages": total, "topics": topics, "max_queue_size": self.max_queue_size}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MessageQueueEngine", "Message"]