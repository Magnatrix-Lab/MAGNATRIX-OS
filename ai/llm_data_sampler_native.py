"""LLM Data Sampler — Native Python (stdlib only)."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class SamplingStrategy(Enum):
    RANDOM = auto()
    STRATIFIED = auto()
    WEIGHTED = auto()
    SYSTEMATIC = auto()

class DataSampler:
    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    def random_sample(self, data: List[Any], n: int) -> List[Any]:
        if n >= len(data):
            return list(data)
        return self._rng.sample(data, n)

    def stratified_sample(self, data: List[Any], n: int, stratifier: Callable[[Any], str]) -> List[Any]:
        groups = {}
        for item in data:
            key = stratifier(item)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        per_group = n // len(groups) if groups else 0
        remainder = n % len(groups) if groups else 0
        result = []
        for i, (key, items) in enumerate(groups.items()):
            take = per_group + (1 if i < remainder else 0)
            if take >= len(items):
                result.extend(items)
            else:
                result.extend(self._rng.sample(items, take))
        return result

    def weighted_sample(self, data: List[Any], weights: List[float], n: int) -> List[Any]:
        if len(data) != len(weights):
            raise ValueError("Data and weights must have same length")
        total = sum(weights)
        probs = [w / total for w in weights]
        result = []
        for _ in range(n):
            r = self._rng.random()
            cumsum = 0.0
            for i, p in enumerate(probs):
                cumsum += p
                if r <= cumsum:
                    result.append(data[i])
                    break
        return result

    def systematic_sample(self, data: List[Any], n: int) -> List[Any]:
        if n >= len(data):
            return list(data)
        step = len(data) // n
        return [data[i * step] for i in range(n)]

    def get_stats(self, original: List[Any], sampled: List[Any]) -> Dict[str, Any]:
        return {"original": len(original), "sampled": len(sampled), "ratio": len(sampled) / len(original) if original else 0.0}

def run() -> None:
    print("Data Sampler test")
    e = DataSampler(seed=42)
    data = list(range(100))
    print("  Random: " + str(e.random_sample(data, 5)))
    print("  Systematic: " + str(e.systematic_sample(data, 5)))
    weighted = e.weighted_sample(["a", "b", "c"], [0.5, 0.3, 0.2], 10)
    print("  Weighted: " + str(weighted))
    print("Data Sampler test complete.")

if __name__ == "__main__":
    run()
