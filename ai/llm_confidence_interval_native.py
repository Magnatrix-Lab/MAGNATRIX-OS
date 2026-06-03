"""Confidence Interval - CI computation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import math

@dataclass
class ConfidenceInterval:
    confidence: float = 0.95

    def compute(self, data: List[float]) -> Tuple[float, float, float]:
        n = len(data)
        if n == 0: return (0.0, 0.0, 0.0)
        mean = sum(data)/n
        var = sum((x-mean)**2 for x in data)/(n-1) if n > 1 else 0
        se = math.sqrt(var/n)
        z = 1.96 if self.confidence >= 0.95 else 1.645
        margin = z * se
        return (round(mean, 4), round(mean - margin, 4), round(mean + margin, 4))

    def stats(self, data: List[float]) -> dict:
        mean, lower, upper = self.compute(data)
        return {"mean": mean, "ci": (lower, upper), "confidence": self.confidence}

def run():
    ci = ConfidenceInterval(0.95)
    data = [10.2, 11.1, 10.8, 10.5, 11.3, 10.9]
    mean, lower, upper = ci.compute(data)
    print(f"CI: [{lower}, {upper}]")
    print("Stats:", ci.stats(data))

if __name__ == "__main__": run()
