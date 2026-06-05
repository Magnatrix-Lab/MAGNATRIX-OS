"""Sizing Optimizer — grade rules, fit, size distribution, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class SizingOptimizer:
    base_size: str = "M"
    measurements: Dict = field(default_factory=dict)
    grade_rules: Dict = field(default_factory=dict)

    def graded_measurement(self, measure_name: str, size_code: str) -> float:
        base = self.measurements.get(measure_name, 0.0)
        step = self.grade_rules.get(measure_name, 2.0)
        size_map = {"XS": -2, "S": -1, "M": 0, "L": 1, "XL": 2, "XXL": 3}
        return base + step * size_map.get(size_code, 0)

    def size_distribution(self, demand: List[float]) -> Dict:
        sizes = ["XS", "S", "M", "L", "XL"]
        total = sum(demand)
        return {s: round(d / total, 3) if total > 0 else 0.0 for s, d in zip(sizes, demand)}

    def stats(self) -> Dict:
        return {"chest_L": round(self.graded_measurement("chest", "L"), 2), "distribution": self.size_distribution([10, 20, 35, 25, 10])}

def run():
    so = SizingOptimizer(measurements={"chest": 96, "waist": 80}, grade_rules={"chest": 4, "waist": 3})
    print(so.stats())

if __name__ == "__main__":
    run()
