"""Edge Scaler - Edge resource scaling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum, auto

class ScaleAction(Enum):
    UP = auto(); DOWN = auto(); HOLD = auto()

@dataclass
class EdgeScaler:
    thresholds: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.thresholds:
            self.thresholds = {"cpu": 0.8, "memory": 0.8, "latency": 100.0}

    def evaluate(self, metrics: Dict[str, float]) -> ScaleAction:
        overload = sum(1 for k, v in metrics.items() if k in self.thresholds and v > self.thresholds[k])
        underload = sum(1 for k, v in metrics.items() if k in self.thresholds and v < self.thresholds[k] * 0.3)
        if overload >= 2: return ScaleAction.UP
        if underload >= 2: return ScaleAction.DOWN
        return ScaleAction.HOLD

    def stats(self, metrics: Dict[str, float]) -> dict:
        return {"action": self.evaluate(metrics).name, "thresholds": self.thresholds}

def run():
    es = EdgeScaler()
    print("Action high:", es.evaluate({"cpu": 0.9, "memory": 0.85, "latency": 120}).name)
    print("Action low:", es.evaluate({"cpu": 0.1, "memory": 0.1, "latency": 20}).name)
    print("Stats:", es.stats({"cpu": 0.5, "memory": 0.5, "latency": 50}))

if __name__ == "__main__": run()
