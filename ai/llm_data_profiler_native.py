"""LLM Data Profiler — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class DataProfiler:
    def __init__(self) -> None:
        pass

    def profile_numeric(self, data: List[float]) -> Dict[str, Any]:
        if not data:
            return {}
        sorted_data = sorted(data)
        n = len(data)
        mean = sum(data) / n
        variance = sum((x - mean) ** 2 for x in data) / n
        std = math.sqrt(variance)
        return {
            "count": n, "mean": mean, "median": sorted_data[n // 2] if n % 2 else (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2,
            "std": std, "min": sorted_data[0], "max": sorted_data[-1], "range": sorted_data[-1] - sorted_data[0],
            "q1": sorted_data[n // 4], "q3": sorted_data[3 * n // 4], "iqr": sorted_data[3 * n // 4] - sorted_data[n // 4]
        }

    def profile_categorical(self, data: List[str]) -> Dict[str, Any]:
        counts = {}
        for v in data:
            counts[v] = counts.get(v, 0) + 1
        total = len(data)
        return {"count": total, "unique": len(counts), "most_common": max(counts.items(), key=lambda x: x[1]), "entropy": -sum(c / total * math.log2(c / total) for c in counts.values() if c > 0)}

    def profile_missing(self, data: List[Any]) -> Dict[str, Any]:
        missing = sum(1 for x in data if x is None or x == "")
        return {"total": len(data), "missing": missing, "missing_pct": missing / len(data) * 100 if data else 0, "complete": len(data) - missing}

    def get_stats(self, data: List[Any]) -> Dict[str, Any]:
        if not data:
            return {}
        if all(isinstance(x, (int, float)) for x in data if x is not None):
            return self.profile_numeric([x for x in data if x is not None])
        return self.profile_categorical([str(x) for x in data if x is not None])

def run() -> None:
    print("Data Profiler test")
    e = DataProfiler()
    numeric = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    print("  Numeric: " + str(e.profile_numeric(numeric)))
    print("  Categorical: " + str(e.profile_categorical(["a", "b", "a", "c", "a"])))
    print("  Stats: " + str(e.get_stats(numeric)))
    print("Data Profiler test complete.")

if __name__ == "__main__":
    run()
