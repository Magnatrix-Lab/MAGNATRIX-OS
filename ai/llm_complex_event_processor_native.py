"""Complex Event Processor - Pattern matching for events for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto
from collections import deque
import time

@dataclass
class EventPattern:
    name: str
    conditions: List[Dict]
    window: float = 10.0

@dataclass
class ComplexEventProcessor:
    events: deque = field(default_factory=lambda: deque())
    patterns: List[EventPattern] = field(default_factory=list)
    matches: List[Dict] = field(default_factory=list)

    def add_event(self, event: Dict) -> None:
        event["time"] = time.time()
        self.events.append(event)
        self._check_patterns()

    def add_pattern(self, pattern: EventPattern) -> None:
        self.patterns.append(pattern)

    def _check_patterns(self) -> None:
        now = time.time()
        for pattern in self.patterns:
            recent = [e for e in self.events if now - e.get("time", 0) <= pattern.window]
            if len(recent) >= len(pattern.conditions):
                self.matches.append({"pattern": pattern.name, "events": recent[:len(pattern.conditions)], "time": now})

    def stats(self) -> dict:
        return {"events": len(self.events), "patterns": len(self.patterns), "matches": len(self.matches)}

def run():
    cep = ComplexEventProcessor()
    cep.add_pattern(EventPattern("alert", [{"type": "error"}, {"type": "error"}], 5.0))
    cep.add_event({"type": "error", "msg": "fail1"})
    cep.add_event({"type": "error", "msg": "fail2"})
    print("Matches:", cep.matches)
    print("Stats:", cep.stats())

if __name__ == "__main__": run()
