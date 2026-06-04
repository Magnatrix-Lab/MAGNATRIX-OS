"""Stream Processor - Real-time event processing for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional
from enum import Enum, auto
from collections import deque
import time

class WindowType(Enum):
    TUMBLING = auto(); SLIDING = auto(); SESSION = auto()

@dataclass
class StreamProcessor:
    window_type: WindowType = WindowType.TUMBLING
    window_size: float = 5.0
    events: deque = field(default_factory=lambda: deque())
    handlers: List[Callable] = field(default_factory=list)

    def add_event(self, event: Dict) -> None:
        event["timestamp"] = time.time()
        self.events.append(event)
        self._cleanup()

    def _cleanup(self) -> None:
        cutoff = time.time() - self.window_size
        while self.events and self.events[0].get("timestamp", 0) < cutoff:
            self.events.popleft()

    def process(self) -> List[Dict]:
        self._cleanup()
        results = []
        for handler in self.handlers:
            results.append(handler(list(self.events)))
        return results

    def stats(self) -> dict:
        return {"window_type": self.window_type.name, "events": len(self.events), "window_size": self.window_size}

def run():
    sp = StreamProcessor(WindowType.TUMBLING, 10.0)
    sp.handlers.append(lambda events: {"count": len(events), "avg": sum(e.get("value", 0) for e in events) / len(events) if events else 0})
    for i in range(5): sp.add_event({"value": i * 10})
    print("Process:", sp.process())
    print("Stats:", sp.stats())

if __name__ == "__main__": run()
