"""Compounding Calculator — dilution, percentage, ratio, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class CompoundingCalculator:
    def simple_dilution(self, c1: float, v1: float, c2: float) -> float:
        return (c1 * v1) / c2 if c2 > 0 else 0.0

    def percentage_solution(self, solute_mg: float, solvent_ml: float) -> float:
        return (solute_mg / 1000) / solvent_ml * 100 if solvent_ml > 0 else 0.0

    def ratio_strength(self, parts: int, total_ml: float) -> float:
        return parts / total_ml if total_ml > 0 else 0.0

    def alligation(self, c_high: float, c_low: float, c_desired: float) -> Tuple[float, float]:
        if c_high == c_low:
            return 1, 1
        high_part = c_desired - c_low
        low_part = c_high - c_desired
        total = high_part + low_part
        return high_part / total, low_part / total

    def final_volume(self, ingredients: List[Tuple[float, float]]) -> float:
        return sum(v for _, v in ingredients)

    def final_concentration(self, solute_mg: float, total_volume_ml: float) -> float:
        return solute_mg / total_volume_ml if total_volume_ml > 0 else 0.0

    def stats(self, c1: float = 10, v1: float = 5, c2: float = 2) -> Dict:
        return {"dilution_volume": round(self.simple_dilution(c1, v1, c2), 2)}

def run():
    cc = CompoundingCalculator()
    print(cc.stats())
    print("Alligation:", cc.alligation(10, 2, 5))
    print("Percentage:", cc.percentage_solution(500, 100))

if __name__ == "__main__":
    run()
