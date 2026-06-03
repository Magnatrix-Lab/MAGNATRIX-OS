"""LLM Statistical Engine — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class StatisticalEngine:
    def __init__(self) -> None:
        pass

    def mean(self, data: List[float]) -> float:
        if not data:
            return 0.0
        return sum(data) / len(data)

    def median(self, data: List[float]) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        n = len(sorted_data)
        if n % 2 == 1:
            return sorted_data[n // 2]
        return (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2

    def mode(self, data: List[float]) -> List[float]:
        if not data:
            return []
        counts = {}
        for v in data:
            counts[v] = counts.get(v, 0) + 1
        max_count = max(counts.values())
        return [k for k, v in counts.items() if v == max_count]

    def variance(self, data: List[float], sample: bool = True) -> float:
        if len(data) < 2:
            return 0.0
        m = self.mean(data)
        squared_diffs = [(x - m) ** 2 for x in data]
        divisor = len(data) - 1 if sample else len(data)
        return sum(squared_diffs) / divisor

    def std_dev(self, data: List[float], sample: bool = True) -> float:
        return math.sqrt(self.variance(data, sample))

    def percentile(self, data: List[float], p: float) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * p / 100
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_data[int(k)]
        d0 = sorted_data[f] * (c - k)
        d1 = sorted_data[c] * (k - f)
        return d0 + d1

    def quartiles(self, data: List[float]) -> Tuple[float, float, float]:
        return (self.percentile(data, 25), self.percentile(data, 50), self.percentile(data, 75))

    def skewness(self, data: List[float]) -> float:
        if len(data) < 3:
            return 0.0
        m = self.mean(data)
        s = self.std_dev(data)
        if s == 0:
            return 0.0
        n = len(data)
        return sum((x - m) ** 3 for x in data) * n / ((n - 1) * (n - 2) * s ** 3)

    def kurtosis(self, data: List[float]) -> float:
        if len(data) < 4:
            return 0.0
        m = self.mean(data)
        s = self.std_dev(data)
        if s == 0:
            return 0.0
        n = len(data)
        return sum((x - m) ** 4 for x in data) * n * (n + 1) / ((n - 1) * (n - 2) * (n - 3) * s ** 4) - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))

    def get_stats(self, data: List[float]) -> Dict[str, Any]:
        return {"count": len(data), "mean": self.mean(data), "median": self.median(data), "std": self.std_dev(data), "min": min(data) if data else 0, "max": max(data) if data else 0, "range": max(data) - min(data) if data else 0}

def run() -> None:
    print("Statistical Engine test")
    e = StatisticalEngine()
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    print("  Mean: " + str(e.mean(data)))
    print("  Median: " + str(e.median(data)))
    print("  Std dev: " + str(e.std_dev(data)))
    print("  Quartiles: " + str(e.quartiles(data)))
    print("  Skewness: " + str(e.skewness(data)))
    print("  Stats: " + str(e.get_stats(data)))
    print("Statistical Engine test complete.")

if __name__ == "__main__":
    run()
