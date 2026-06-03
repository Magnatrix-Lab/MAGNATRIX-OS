"""LLM Weight Inspector — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class WeightStatus(Enum):
    HEALTHY = auto()
    DEGENERATE = auto()
    VANISHING = auto()
    EXPLODING = auto()
    DEAD = auto()

class WeightInspector:
    def __init__(self) -> None:
        self._weights: Dict[str, List[float]] = {}

    def register_weights(self, name: str, weights: List[float]) -> None:
        self._weights[name] = weights

    def analyze(self, name: str) -> Dict[str, Any]:
        weights = self._weights.get(name, [])
        if not weights:
            return {}
        mean = sum(weights) / len(weights)
        variance = sum((w - mean) ** 2 for w in weights) / len(weights)
        std = math.sqrt(variance)
        max_w = max(weights)
        min_w = min(weights)
        status = WeightStatus.HEALTHY
        if max_w > 100 or min_w < -100:
            status = WeightStatus.EXPLODING
        elif max_w < 0.001 and min_w > -0.001:
            status = WeightStatus.VANISHING
        elif all(w == 0 for w in weights):
            status = WeightStatus.DEAD
        return {"mean": mean, "std": std, "min": min_w, "max": max_w, "status": status.name, "count": len(weights)}

    def get_all_stats(self) -> Dict[str, Any]:
        return {name: self.analyze(name) for name in self._weights}

def run() -> None:
    print("Weight Inspector test")
    e = WeightInspector()
    e.register_weights("layer1", [0.1, 0.2, -0.1, 0.05, 0.0])
    e.register_weights("layer2", [100.0, -50.0, 200.0, 0.0])
    e.register_weights("layer3", [0.0001, 0.0002, -0.0001, 0.0])
    for name in ["layer1", "layer2", "layer3"]:
        print("  " + name + ": " + str(e.analyze(name)))
    print("Weight Inspector test complete.")

if __name__ == "__main__":
    run()
