"""LLM Data Transformer — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class DataTransformer:
    def __init__(self) -> None:
        pass

    def normalize(self, data: List[float]) -> List[float]:
        min_v = min(data)
        max_v = max(data)
        range_v = max_v - min_v
        if range_v == 0:
            return [0.0] * len(data)
        return [(x - min_v) / range_v for x in data]

    def standardize(self, data: List[float]) -> List[float]:
        mean = sum(data) / len(data)
        std = math.sqrt(sum((x - mean) ** 2 for x in data) / len(data))
        if std == 0:
            return [0.0] * len(data)
        return [(x - mean) / std for x in data]

    def log_transform(self, data: List[float]) -> List[float]:
        return [math.log(x) if x > 0 else 0.0 for x in data]

    def sqrt_transform(self, data: List[float]) -> List[float]:
        return [math.sqrt(x) if x >= 0 else 0.0 for x in data]

    def binarize(self, data: List[float], threshold: float) -> List[int]:
        return [1 if x >= threshold else 0 for x in data]

    def get_stats(self, data: List[float]) -> Dict[str, Any]:
        return {"count": len(data), "min": min(data), "max": max(data), "mean": sum(data) / len(data) if data else 0}

def run() -> None:
    print("Data Transformer test")
    e = DataTransformer()
    data = [1, 2, 3, 4, 5]
    print("  Normalize: " + str(e.normalize(data)))
    print("  Standardize: " + str(e.standardize(data)))
    print("  Binarize: " + str(e.binarize(data, 3)))
    print("  Stats: " + str(e.get_stats(data)))
    print("Data Transformer test complete.")

if __name__ == "__main__":
    run()
