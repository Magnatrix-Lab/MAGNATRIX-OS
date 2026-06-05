"""Dating Estimator — radiocarbon, dendrochronology, relative, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class DatingEstimator:
    half_life_c14: float = 5730.0

    def radiocarbon_date(self, remaining_pct: float) -> float:
        if remaining_pct <= 0:
            return 0.0
        return -self.half_life_c14 * math.log(remaining_pct / 100) / math.log(2)

    def calibration_curve(self, raw_bp: float, calibration_table: List[Tuple[float, float]]) -> float:
        if not calibration_table:
            return raw_bp
        closest = min(calibration_table, key=lambda x: abs(x[0] - raw_bp))
        return closest[1]

    def relative_date(self, stratigraphic_position: float, max_depth: float, max_age: float) -> float:
        return stratigraphic_position / max_depth * max_age if max_depth > 0 else 0.0

    def dendrochronology_match(self, ring_pattern: List[int], master_chronology: List[List[int]]) -> Optional[int]:
        best_match = None
        best_score = float('inf')
        for i, chron in enumerate(master_chronology):
            if len(ring_pattern) != len(chron):
                continue
            score = sum(abs(a - b) for a, b in zip(ring_pattern, chron))
            if score < best_score:
                best_score = score
                best_match = i
        return best_match

    def stats(self, remaining_pct: float) -> Dict:
        return {"raw_bp": round(self.radiocarbon_date(remaining_pct), 0)}

def run():
    de = DatingEstimator()
    print(de.stats(50))
    print("50% =", de.radiocarbon_date(50), "years BP")
    print("25% =", de.radiocarbon_date(25), "years BP")

if __name__ == "__main__":
    run()
