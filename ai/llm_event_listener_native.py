"""LLM Event Listener — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class EventPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

@dataclass
class Event:
    id: str
    event_type: str
    payload: Dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class EventListener:
    def __init__(self) -> None:
        self._handlers: Dict[str, List[tuple]] = {}
        self._history: List[Event] = []
        self._muted: set = set()

    def on(self, event_type: str, handler: Callable[[Event], None], priority: EventPriority = EventPriority.NORMAL) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: x[0].value)

    def off(self, event_type: str) -> None:
        if event_type in self._handlers:
            del self._handlers[event_type]

    def mute(self, event_type: str) -> None:
        self._muted.add(event_type)

    def unmute(self, event_type: str) -> None:
        self._muted.discard(event_type)

    def emit(self, event: Event) -> None:
        self._history.append(event)
        if event.event_type in self._muted:
            return
        handlers = self._handlers.get(event.event_type, [])
        for _, handler in handlers:
            handler(event)

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for e in self._history:
            counts[e.event_type] = counts.get(e.event_type, 0) + 1
        return {"total": len(self._history), "by_type": counts, "handlers": sum(len(h) for h in self._handlers.values()), "muted": len(self._muted)}

def run() -> None:
    print("Event Listener test")
    e = EventListener()
    e.on("user.login", lambda ev: print("  User logged in: " + ev.id))
    e.on("data.update", lambda ev: print("  Data updated: " + ev.id), EventPriority.HIGH)
    e.emit(Event("e1", "user.login", {"user": "alice"}))
    e.emit(Event("e2", "data.update", {"table": "users"}))
    e.mute("user.login")
    e.emit(Event("e3", "user.login", {"user": "bob"}))
    print("  Stats: " + str(e.get_stats()))
    print("Event Listener test complete.")

if __name__ == "__main__":
    run()
