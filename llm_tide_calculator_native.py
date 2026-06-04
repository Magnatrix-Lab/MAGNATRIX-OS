"""Tide Calculator — harmonic constituents, tidal range, predictions, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class TideCalculator:
    constituents: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    """name -> (amplitude, phase)"""

    def add_constituent(self, name: str, amp: float, phase: float):
        self.constituents[name] = (amp, phase)

    def predict(self, t: float) -> float:
        """t in hours from reference."""
        height = 0.0
        speeds = {"M2": 28.984, "S2": 30.0, "N2": 28.44, "K1": 15.041, "O1": 13.943}
        for name, (amp, phase) in self.constituents.items():
            speed = speeds.get(name, 15.0)
            height += amp * math.cos(math.radians(speed * t - phase))
        return height

    def high_low_tides(self, hours: List[float]) -> Tuple[float, float]:
        heights = [self.predict(h) for h in hours]
        return max(heights), min(heights)

    def tidal_range(self, hours: List[float]) -> float:
        high, low = self.high_low_tides(hours)
        return high - low

    def stats(self) -> Dict:
        return {"constituents": len(self.constituents), "names": list(self.constituents.keys())}

def run():
    tc = TideCalculator()
    tc.add_constituent("M2", 1.2, 0)
    tc.add_constituent("S2", 0.5, 30)
    print("Height t=0:", tc.predict(0))
    print("Range 24h:", tc.tidal_range(list(range(24))))
    print(tc.stats())

if __name__ == "__main__":
    run()
