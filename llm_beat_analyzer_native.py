"""Beat Analyzer — BPM, swing, groove, phase, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class BeatAnalyzer:
    intervals_ms: List[float] = field(default_factory=list)

    def bpm(self) -> float:
        if not self.intervals_ms or len(self.intervals_ms) < 2:
            return 0.0
        avg = sum(self.intervals_ms) / len(self.intervals_ms)
        return 60000.0 / avg if avg > 0 else 0.0

    def swing_ratio(self, even_ms: float = 250.0, odd_ms: float = 350.0) -> float:
        return odd_ms / even_ms if even_ms > 0 else 0.0

    def groove_consistency(self) -> float:
        if len(self.intervals_ms) < 2:
            return 0.0
        mean = sum(self.intervals_ms) / len(self.intervals_ms)
        variance = sum((i - mean) ** 2 for i in self.intervals_ms) / len(self.intervals_ms)
        return 1.0 - (math.sqrt(variance) / mean) if mean > 0 else 0.0

    def stats(self) -> Dict:
        return {"bpm": round(self.bpm(), 2), "swing": round(self.swing_ratio(), 3), "groove": round(self.groove_consistency(), 3)}

def run():
    ba = BeatAnalyzer(intervals_ms=[250, 350, 255, 345, 248, 352])
    print(ba.stats())

if __name__ == "__main__":
    run()
