"""Event Window - Time-based windows for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
from collections import deque
import time

@dataclass
class EventWindow:
    window_size: float = 5.0
    slide: float = 2.0
    events: deque = field(default_factory=lambda: deque())

    def add(self, event: Dict) -> None:
        event["time"] = time.time()
        self.events.append(event)

    def get_window(self, current_time: float = None) -> List[Dict]:
        if current_time is None: current_time = time.time()
        cutoff = current_time - self.window_size
        return [e for e in self.events if e.get("time", 0) >= cutoff]

    def aggregate(self, current_time: float = None) -> Dict:
        window = self.get_window(current_time)
        if not window: return {}
        values = [e.get("value", 0) for e in window]
        return {"count": len(window), "sum": sum(values), "avg": sum(values)/len(values), "min": min(values), "max": max(values)}

    def stats(self) -> dict:
        return {"window_size": self.window_size, "events": len(self.events), "current_window": len(self.get_window())}

def run():
    ew = EventWindow(5.0, 2.0)
    for i in range(10): ew.add({"value": i})
    print("Aggregate:", ew.aggregate())
    print("Stats:", ew.stats())

if __name__ == "__main__": run()
