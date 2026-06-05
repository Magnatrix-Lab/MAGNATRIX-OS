"""Salary Benchmark — percentile, range, compa-ratio, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class SalaryBenchmark:
    data: List[float] = field(default_factory=list)

    def percentile(self, value: float) -> float:
        if not self.data:
            return 0.0
        below = sum(1 for d in self.data if d < value)
        return below / len(self.data) * 100

    def median(self) -> float:
        if not self.data:
            return 0.0
        s = sorted(self.data)
        n = len(s)
        return s[n//2] if n % 2 == 1 else (s[n//2 - 1] + s[n//2]) / 2

    def range_spread(self) -> float:
        if not self.data:
            return 0.0
        return (max(self.data) - min(self.data)) / min(self.data) if min(self.data) > 0 else 0.0

    def compa_ratio(self, salary: float, target: float) -> float:
        return salary / target if target > 0 else 0.0

    def market_adjustment(self, salary: float, target_percentile: float = 0.5) -> float:
        if not self.data:
            return 0.0
        idx = int(len(self.data) * target_percentile)
        target = sorted(self.data)[min(idx, len(self.data) - 1)]
        return target - salary

    def stats(self, salary: float = 0) -> Dict:
        return {
            "median": self.median(),
            "range_spread": round(self.range_spread(), 3),
            "percentile": round(self.percentile(salary), 1) if salary > 0 else None
        }

def run():
    sb = SalaryBenchmark([50000, 55000, 60000, 65000, 70000, 75000, 80000, 90000, 100000])
    print(sb.stats(72000))
    print("Compa-ratio:", sb.compa_ratio(72000, 70000))
    print("Adjustment to 75th:", sb.market_adjustment(72000, 0.75))

if __name__ == "__main__":
    run()
