"""Chronograph — lap time, split, average, reset, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Chronograph:
    laps: List[float] = field(default_factory=list)
    running: bool = False
    start_time: float = 0.0

    def lap(self, current_time: float) -> float:
        if self.running:
            lap_time = current_time - self.start_time
            self.laps.append(lap_time)
            self.start_time = current_time
            return lap_time
        return 0.0

    def split(self) -> float:
        if self.laps:
            return sum(self.laps)
        return 0.0

    def average_lap(self) -> float:
        if not self.laps:
            return 0.0
        return sum(self.laps) / len(self.laps)

    def best_lap(self) -> float:
        if not self.laps:
            return 0.0
        return min(self.laps)

    def reset(self):
        self.laps = []
        self.running = False

    def stats(self) -> Dict:
        return {"laps": len(self.laps), "total": round(self.split(), 2), "avg": round(self.average_lap(), 2), "best": round(self.best_lap(), 2)}

def run():
    c = Chronograph()
    c.laps = [12.5, 11.8, 13.2, 12.0]
    print(c.stats())
    c.reset()
    print(c.stats())

if __name__ == "__main__":
    run()
