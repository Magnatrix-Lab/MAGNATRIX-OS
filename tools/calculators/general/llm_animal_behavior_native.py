"""Animal Behavior — ethogram, frequency, duration, stereotypy, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class BehaviorEvent:
    behavior: str
    start: float
    end: float

class AnimalBehavior:
    def __init__(self):
        self.events: List[BehaviorEvent] = []

    def add_event(self, e: BehaviorEvent):
        self.events.append(e)

    def frequency(self, behavior: str) -> int:
        return sum(1 for e in self.events if e.behavior == behavior)

    def total_duration(self, behavior: str) -> float:
        return sum(e.end - e.start for e in self.events if e.behavior == behavior)

    def ethogram(self) -> Dict[str, Dict]:
        result = {}
        for e in self.events:
            if e.behavior not in result:
                result[e.behavior] = {"freq": 0, "dur": 0.0}
            result[e.behavior]["freq"] += 1
            result[e.behavior]["dur"] += e.end - e.start
        return result

    def stereotypy_index(self) -> float:
        if not self.events:
            return 0.0
        total = len(self.events)
        max_freq = max(self.frequency(b) for b in set(e.behavior for e in self.events))
        return max_freq / total

    def time_budget(self) -> Dict[str, float]:
        total_time = max(e.end for e in self.events) if self.events else 1
        etho = self.ethogram()
        return {b: d["dur"] / total_time for b, d in etho.items()}

    def stats(self) -> Dict:
        return {"events": len(self.events), "behaviors": len(set(e.behavior for e in self.events)), "stereotypy": round(self.stereotypy_index(), 3)}

def run():
    ab = AnimalBehavior()
    ab.add_event(BehaviorEvent("graze", 0, 30))
    ab.add_event(BehaviorEvent("rest", 30, 60))
    ab.add_event(BehaviorEvent("graze", 60, 90))
    print(ab.stats())
    print("Ethogram:", ab.ethogram())
    print("Time budget:", ab.time_budget())

if __name__ == "__main__":
    run()
