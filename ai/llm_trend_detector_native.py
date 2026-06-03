"""Trend Detector - Linear/nonlinear trend detection for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum, auto
import math

class TrendType(Enum):
    UPWARD = auto()
    DOWNWARD = auto()
    STATIONARY = auto()
    CYCLIC = auto()

@dataclass
class TrendDetector:
    window: int = 5
    threshold: float = 0.1

    def linear_fit(self, data: List[float]) -> Tuple[float, float]:
        n = len(data)
        x = list(range(n))
        mean_x = sum(x) / n
        mean_y = sum(data) / n
        ss_xy = sum((x[i] - mean_x) * (data[i] - mean_y) for i in range(n))
        ss_xx = sum((x[i] - mean_x) ** 2 for i in range(n))
        slope = ss_xy / ss_xx if ss_xx != 0 else 0
        intercept = mean_y - slope * mean_x
        return slope, intercept

    def detect(self, data: List[float]) -> TrendType:
        slope, _ = self.linear_fit(data)
        if abs(slope) < self.threshold:
            return TrendType.STATIONARY
        return TrendType.UPWARD if slope > 0 else TrendType.DOWNWARD

    def forecast(self, data: List[float], steps: int = 3) -> List[float]:
        slope, intercept = self.linear_fit(data)
        n = len(data)
        return [slope * (n + i) + intercept for i in range(steps)]

    def stats(self, data: List[float]) -> dict:
        slope, intercept = self.linear_fit(data)
        return {"slope": round(slope, 6), "intercept": round(intercept, 4), "trend": self.detect(data).name}

def run():
    td = TrendDetector()
    data = [1, 2, 3, 4, 5, 6, 7, 8]
    print("Trend:", td.detect(data).name)
    print("Forecast:", [round(v, 4) for v in td.forecast(data, 3)])
    print("Stats:", td.stats(data))

if __name__ == "__main__":
    run()
