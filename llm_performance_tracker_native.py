"""Performance Tracker — metrics, PRs, trends, benchmarks, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class PerformanceTracker:
    metric_name: str = ""
    values: List[float] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)

    def personal_record(self) -> float:
        return max(self.values) if self.values else 0.0

    def average(self) -> float:
        return sum(self.values) / len(self.values) if self.values else 0.0

    def trend(self) -> str:
        if len(self.values) < 2:
            return "stable"
        first_half = sum(self.values[:len(self.values)//2]) / max(1, len(self.values)//2)
        second_half = sum(self.values[len(self.values)//2:]) / max(1, len(self.values) - len(self.values)//2)
        if second_half > first_half * 1.02:
            return "improving"
        elif second_half < first_half * 0.98:
            return "declining"
        return "stable"

    def improvement_rate(self) -> float:
        if len(self.values) < 2:
            return 0.0
        return (self.values[-1] - self.values[0]) / len(self.values)

    def percentile(self, value: float, population: List[float]) -> float:
        if not population:
            return 0.0
        below = sum(1 for p in population if p < value)
        return below / len(population) * 100

    def stats(self) -> Dict:
        return {"pr": self.personal_record(), "avg": round(self.average(), 2), "trend": self.trend()}

def run():
    pt = PerformanceTracker("5k_time", [1200, 1180, 1150, 1120, 1100])
    print(pt.stats())
    print("Improvement:", pt.improvement_rate())

if __name__ == "__main__":
    run()
