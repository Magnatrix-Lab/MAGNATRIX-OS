"""LLM Message Bus — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto
import queue

class ChannelType(Enum):
    DIRECT = auto()
    BROADCAST = auto()
    TOPIC = auto()
    QUEUE = auto()

@dataclass
class Message:
    id: str
    channel: str
    payload: Dict[str, Any]
    sender: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class MessageBus:
    def __init__(self) -> None:
        self._channels: Dict[str, List[Callable[[Message], None]]] = {}
        self._queues: Dict[str, queue.Queue] = {}
        self._history: List[Message] = []

    def subscribe(self, channel: str, handler: Callable[[Message], None]) -> None:
        if channel not in self._channels:
            self._channels[channel] = []
        self._channels[channel].append(handler)

    def unsubscribe(self, channel: str, handler: Callable[[Message], None]) -> None:
        if channel in self._channels:
            self._channels[channel] = [h for h in self._channels[channel] if h != handler]

    def publish(self, message: Message) -> None:
        self._history.append(message)
        handlers = self._channels.get(message.channel, [])
        for handler in handlers:
            handler(message)

    def create_queue(self, channel: str) -> None:
        self._queues[channel] = queue.Queue()

    def enqueue(self, message: Message) -> None:
        if message.channel in self._queues:
            self._queues[message.channel].put(message)

    def dequeue(self, channel: str) -> Optional[Message]:
        if channel in self._queues:
            try:
                return self._queues[channel].get(block=False)
            except queue.Empty:
                return None
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {"channels": len(self._channels), "queues": len(self._queues), "messages": len(self._history)}

def run() -> None:
    print("Message Bus test")
    e = MessageBus()
    e.subscribe("updates", lambda m: print("  [updates] " + m.id + ": " + str(m.payload)))
    e.subscribe("alerts", lambda m: print("  [alerts] " + m.id + ": " + str(m.payload)))
    e.publish(Message("m1", "updates", {"status": "ok"}))
    e.publish(Message("m2", "alerts", {"level": "critical"}))
    e.create_queue("jobs")
    e.enqueue(Message("j1", "jobs", {"task": "train"}))
    msg = e.dequeue("jobs")
    print("  Dequeued: " + (msg.id if msg else "None"))
    print("  Stats: " + str(e.get_stats()))
    print("Message Bus test complete.")

if __name__ == "__main__":
    run()
