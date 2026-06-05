"""Event Bus — decoupled event distribution, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any, Optional
from enum import Enum, auto
import time
import uuid

class EventPriority(Enum):
    HIGH = 1
    NORMAL = 2
    LOW = 3

@dataclass
class BusEvent:
    event_id: str
    event_type: str
    payload: Any
    priority: EventPriority = EventPriority.NORMAL
    timestamp: float = field(default_factory=time.time)

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.history: List[BusEvent] = []
        self.event_count: Dict[str, int] = {}

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: Any, priority: EventPriority = EventPriority.NORMAL):
        event_id = str(uuid.uuid4())[:8]
        event = BusEvent(event_id, event_type, payload, priority)
        self.history.append(event)
        self.event_count[event_type] = self.event_count.get(event_type, 0) + 1
        for handler in self.subscribers.get(event_type, []):
            try:
                handler(event)
            except:
                pass

    def get_history(self, event_type: Optional[str] = None) -> List[BusEvent]:
        if event_type:
            return [e for e in self.history if e.event_type == event_type]
        return self.history

    def stats(self) -> Dict:
        return {"subscribers": {k: len(v) for k, v in self.subscribers.items()}, "events": len(self.history), "event_types": len(self.event_count)}

def run():
    bus = EventBus()
    received = []
    def handler(event):
        received.append(event.payload)
    bus.subscribe("order.created", handler)
    bus.publish("order.created", {"id": 1, "total": 100})
    bus.publish("order.created", {"id": 2, "total": 200})
    print(received)
    print(bus.stats())

if __name__ == "__main__":
    run()
