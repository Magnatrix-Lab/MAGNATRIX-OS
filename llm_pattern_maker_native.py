"""Pattern Maker — grading, nesting, marker efficiency, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class PatternMaker:
    pieces: List[Dict] = field(default_factory=list)
    fabric_width_m: float = 1.5

    def total_piece_area(self) -> float:
        return sum(p.get("width", 0) * p.get("length", 0) for p in self.pieces)

    def marker_efficiency(self) -> float:
        if not self.pieces:
            return 0.0
        used = self.total_piece_area()
        theoretical_length = used / self.fabric_width_m if self.fabric_width_m > 0 else 0.0
        return min(1.0, used / (theoretical_length * self.fabric_width_m + 0.001)) if theoretical_length > 0 else 0.0

    def grade_size(self, base_measurement: float, size_step: float = 2.0, steps: int = 1) -> float:
        return base_measurement + size_step * steps

    def stats(self) -> Dict:
        return {"piece_area_m2": round(self.total_piece_area(), 2), "efficiency": round(self.marker_efficiency(), 3)}

def run():
    pm = PatternMaker(pieces=[{"width": 0.5, "length": 0.8}, {"width": 0.3, "length": 0.6}], fabric_width_m=1.5)
    print(pm.stats())

if __name__ == "__main__":
    run()
