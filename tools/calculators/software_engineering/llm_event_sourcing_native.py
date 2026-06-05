"""Event Sourcing — event store, aggregate replay, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum, auto
import time
import uuid
import json

class EventType(Enum):
    CREATE = auto()
    UPDATE = auto()
    DELETE = auto()
    CUSTOM = auto()

@dataclass
class DomainEvent:
    event_id: str
    aggregate_id: str
    event_type: EventType
    payload: Dict
    version: int
    timestamp: float = field(default_factory=time.time)

class EventStore:
    def __init__(self):
        self.events: List[DomainEvent] = []
        self.streams: Dict[str, List[DomainEvent]] = {}

    def append(self, aggregate_id: str, event_type: EventType, payload: Dict, version: int) -> DomainEvent:
        event_id = str(uuid.uuid4())[:8]
        event = DomainEvent(event_id, aggregate_id, event_type, payload, version)
        self.events.append(event)
        if aggregate_id not in self.streams:
            self.streams[aggregate_id] = []
        self.streams[aggregate_id].append(event)
        return event

    def get_stream(self, aggregate_id: str) -> List[DomainEvent]:
        return self.streams.get(aggregate_id, [])

    def replay(self, aggregate_id: str, handler: Callable[[DomainEvent], None]):
        for event in self.get_stream(aggregate_id):
            handler(event)

    def get_all_events(self) -> List[DomainEvent]:
        return self.events

    def stats(self) -> Dict:
        return {"total_events": len(self.events), "streams": len(self.streams), "latest_version": max(e.version for e in self.events) if self.events else 0}

def run():
    store = EventStore()
    store.append("user_1", EventType.CREATE, {"name": "Alice"}, 1)
    store.append("user_1", EventType.UPDATE, {"name": "Alice Smith"}, 2)
    store.append("user_2", EventType.CREATE, {"name": "Bob"}, 1)
    print(store.get_stream("user_1"))
    print(store.stats())

if __name__ == "__main__":
    run()
