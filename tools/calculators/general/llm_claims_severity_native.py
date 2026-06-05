"""Native stdlib module: Claims Severity Model
Models claims severity by distribution fitting and tail risk estimation.
"""
from dataclasses import dataclass, field
from typing import List, Dict
import math

@dataclass
class ClaimsSeverityModel:
    line_of_business: str
    claim_amounts: List[float] = field(default_factory=list)

    def count(self) -> int:
        return len(self.claim_amounts)

    def mean(self) -> float:
        if not self.claim_amounts:
            return 0.0
        return sum(self.claim_amounts) / len(self.claim_amounts)

    def median(self) -> float:
        if not self.claim_amounts:
            return 0.0
        sorted_vals = sorted(self.claim_amounts)
        mid = len(sorted_vals) // 2
        if len(sorted_vals) % 2 == 1:
            return sorted_vals[mid]
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2

    def std_dev(self) -> float:
        if len(self.claim_amounts) < 2:
            return 0.0
        m = self.mean()
        variance = sum((x - m) ** 2 for x in self.claim_amounts) / (len(self.claim_amounts) - 1)
        return math.sqrt(variance)

    def coef_variation(self) -> float:
        if self.mean() == 0:
            return 0.0
        return self.std_dev() / self.mean()

    def tail_pct(self, percentile: float = 95) -> float:
        if not self.claim_amounts:
            return 0.0
        sorted_vals = sorted(self.claim_amounts)
        idx = int(len(sorted_vals) * (percentile / 100))
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    def stats(self) -> Dict:
        return {
            "line": self.line_of_business,
            "count": self.count(),
            "mean": round(self.mean(), 2),
            "median": round(self.median(), 2),
            "std_dev": round(self.std_dev(), 2),
            "coef_variation": round(self.coef_variation(), 3),
            "p95": round(self.tail_pct(95), 2),
            "p99": round(self.tail_pct(99), 2),
        }

def run():
    csm = ClaimsSeverityModel(
        line_of_business="General Liability",
        claim_amounts=[5000, 8000, 12000, 15000, 20000, 25000, 35000, 50000, 75000, 120000, 250000]
    )
    print(csm.stats())

if __name__ == "__main__":
    run()
