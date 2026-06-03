"""LLM Data Imputer — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class DataImputer:
    def __init__(self) -> None:
        pass

    def mean_impute(self, data: List[float]) -> List[float]:
        valid = [x for x in data if x is not None]
        if not valid:
            return data
        mean = sum(valid) / len(valid)
        return [x if x is not None else mean for x in data]

    def median_impute(self, data: List[float]) -> List[float]:
        valid = sorted([x for x in data if x is not None])
        if not valid:
            return data
        median = valid[len(valid) // 2] if len(valid) % 2 == 1 else (valid[len(valid) // 2 - 1] + valid[len(valid) // 2]) / 2
        return [x if x is not None else median for x in data]

    def mode_impute(self, data: List[Any]) -> List[Any]:
        counts = {}
        for x in data:
            if x is not None:
                counts[x] = counts.get(x, 0) + 1
        if not counts:
            return data
        mode = max(counts.items(), key=lambda x: x[1])[0]
        return [x if x is not None else mode for x in data]

    def forward_fill(self, data: List[Any]) -> List[Any]:
        result = []
        last = None
        for x in data:
            if x is not None:
                last = x
            result.append(last if last is not None else x)
        return result

    def backward_fill(self, data: List[Any]) -> List[Any]:
        result = list(data)
        for i in range(len(result) - 2, -1, -1):
            if result[i] is None:
                result[i] = result[i + 1]
        return result

    def get_stats(self, data: List[Any]) -> Dict[str, Any]:
        missing = sum(1 for x in data if x is None)
        return {"total": len(data), "missing": missing, "missing_pct": missing / len(data) * 100 if data else 0}

def run() -> None:
    print("Data Imputer test")
    e = DataImputer()
    data = [1.0, 2.0, None, 4.0, None, 6.0]
    print("  Mean impute: " + str(e.mean_impute(data)))
    print("  Median impute: " + str(e.median_impute(data)))
    print("  Forward fill: " + str(e.forward_fill(data)))
    print("  Stats: " + str(e.get_stats(data)))
    print("Data Imputer test complete.")

if __name__ == "__main__":
    run()
