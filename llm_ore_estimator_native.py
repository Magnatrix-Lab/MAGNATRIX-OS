"""Ore Estimator — grade, tonnage, cutoff, reserve, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class OreEstimator:
    samples: List[Tuple[float, float]] = field(default_factory=list)
    """(grade_pct, tonnage)"""
    cutoff_grade: float = 0.5

    def above_cutoff(self) -> List[Tuple[float, float]]:
        return [(g, t) for g, t in self.samples if g >= self.cutoff_grade]

    def total_tonnage(self) -> float:
        return sum(t for _, t in self.above_cutoff())

    def average_grade(self) -> float:
        above = self.above_cutoff()
        if not above:
            return 0.0
        total_t = sum(t for _, t in above)
        return sum(g * t for g, t in above) / total_t if total_t > 0 else 0.0

    def metal_content(self) -> float:
        return self.total_tonnage() * self.average_grade() / 100

    def net_present_value(self, metal_price: float, mining_cost: float, processing_cost: float, recovery: float = 0.9) -> float:
        metal = self.metal_content() * recovery
        revenue = metal * metal_price
        cost = self.total_tonnage() * (mining_cost + processing_cost)
        return revenue - cost

    def stats(self) -> Dict:
        return {"tonnage": round(self.total_tonnage(), 0), "avg_grade": round(self.average_grade(), 2), "metal_content": round(self.metal_content(), 1)}

def run():
    oe = OreEstimator([(1.2, 100000), (0.8, 150000), (0.4, 200000), (0.6, 120000)], cutoff_grade=0.5)
    print(oe.stats())
    print("NPV:", oe.net_present_value(50, 30, 20))

if __name__ == "__main__":
    run()
