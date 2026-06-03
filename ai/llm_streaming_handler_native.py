"""LLM Streaming Handler — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class StreamEventType(Enum):
    START = auto()
    CONTENT = auto()
    ERROR = auto()
    END = auto()

@dataclass
class StreamEvent:
    event_type: StreamEventType
    data: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class StreamingHandler:
    def __init__(self) -> None:
        self._handlers: Dict[StreamEventType, Callable[[StreamEvent], None]] = {}
        self._buffer: List[str] = []
        self._events: List[StreamEvent] = []

    def on(self, event_type: StreamEventType, handler: Callable[[StreamEvent], None]) -> None:
        self._handlers[event_type] = handler

    def emit(self, event: StreamEvent) -> None:
        self._events.append(event)
        handler = self._handlers.get(event.event_type)
        if handler:
            handler(event)
        if event.event_type == StreamEventType.CONTENT:
            self._buffer.append(event.data)

    def get_buffer(self) -> str:
        return "".join(self._buffer)

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for e in self._events:
            counts[e.event_type.name] = counts.get(e.event_type.name, 0) + 1
        return {"events": len(self._events), "by_type": counts, "buffer_length": len(self.get_buffer())}

def run() -> None:
    print("Streaming Handler test")
    e = StreamingHandler()
    e.on(StreamEventType.START, lambda ev: print("  [START]"))
    e.on(StreamEventType.CONTENT, lambda ev: print("  [CONTENT] " + ev.data))
    e.on(StreamEventType.END, lambda ev: print("  [END]"))
    e.emit(StreamEvent(StreamEventType.START, ""))
    e.emit(StreamEvent(StreamEventType.CONTENT, "Hello"))
    e.emit(StreamEvent(StreamEventType.CONTENT, " world"))
    e.emit(StreamEvent(StreamEventType.CONTENT, "!"))
    e.emit(StreamEvent(StreamEventType.END, ""))
    print("  Full buffer: '" + e.get_buffer() + "'")
    print("  Stats: " + str(e.get_stats()))
    print("Streaming Handler test complete.")

if __name__ == "__main__":
    run()
