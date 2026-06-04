"""Threat Detector - Anomaly detection for security for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math
from collections import defaultdict

class ThreatLevel(Enum):
    LOW = auto(); MEDIUM = auto(); HIGH = auto(); CRITICAL = auto()

@dataclass
class ThreatDetector:
    baseline: Dict[str, float] = field(default_factory=dict)
    threshold: float = 2.0
    
    def set_baseline(self, metric: str, mean: float, std: float) -> None:
        self.baseline[metric] = {"mean": mean, "std": std}
    
    def detect(self, metric: str, value: float) -> ThreatLevel:
        if metric not in self.baseline:
            return ThreatLevel.LOW
        stats = self.baseline[metric]
        z_score = abs(value - stats["mean"]) / stats["std"] if stats["std"] > 0 else 0
        if z_score > self.threshold * 3: return ThreatLevel.CRITICAL
        elif z_score > self.threshold * 2: return ThreatLevel.HIGH
        elif z_score > self.threshold: return ThreatLevel.MEDIUM
        return ThreatLevel.LOW
    
    def stats(self) -> dict:
        return {"baselines": len(self.baseline), "threshold": self.threshold}

def run():
    td = ThreatDetector(2.0)
    td.set_baseline("cpu", 50.0, 10.0)
    td.set_baseline("requests", 1000.0, 200.0)
    for value in [45, 70, 85, 95]:
        level = td.detect("cpu", value)
        print(f"CPU {value}% -> {level.name}")
    print("Stats:", td.stats())

if __name__ == "__main__": run()
