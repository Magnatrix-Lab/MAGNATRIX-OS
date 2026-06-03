"""LLM Trend Detector — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class TrendDirection(Enum):
    UP = auto()
    DOWN = auto()
    STABLE = auto()
    VOLATILE = auto()

class TrendDetector:
    def __init__(self) -> None:
        self._series: Dict[str, List[float]] = {}

    def add_series(self, name: str) -> None:
        if name not in self._series:
            self._series[name] = []

    def add_point(self, name: str, value: float) -> None:
        if name not in self._series:
            self._series[name] = []
        self._series[name].append(value)

    def detect_trend(self, name: str, window: int = 5) -> Dict[str, Any]:
        values = self._series.get(name, [])
        if len(values) < 2:
            return {"direction": TrendDirection.STABLE.name, "slope": 0.0, "strength": 0.0}
        recent = values[-window:]
        if len(recent) < 2:
            recent = values
        x = list(range(len(recent)))
        n = len(recent)
        sum_x = sum(x)
        sum_y = sum(recent)
        sum_xy = sum(xi * yi for xi, yi in zip(x, recent))
        sum_x2 = sum(xi * xi for xi in x)
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0.0
        avg = sum_y / n if n > 0 else 0.0
        variance = sum((y - avg) ** 2 for y in recent) / n if n > 0 else 0.0
        std = variance ** 0.5
        if std > abs(slope) * 3:
            direction = TrendDirection.VOLATILE
        elif slope > 0.01:
            direction = TrendDirection.UP
        elif slope < -0.01:
            direction = TrendDirection.DOWN
        else:
            direction = TrendDirection.STABLE
        return {"direction": direction.name, "slope": slope, "strength": abs(slope) / (std + 0.001)}

    def detect_change_point(self, name: str) -> Optional[int]:
        values = self._series.get(name, [])
        if len(values) < 3:
            return None
        for i in range(1, len(values) - 1):
            left_avg = sum(values[:i]) / i if i > 0 else 0
            right_avg = sum(values[i:]) / (len(values) - i) if len(values) > i else 0
            if abs(left_avg - right_avg) > 0.5 * max(abs(left_avg), abs(right_avg), 0.001):
                return i
        return None

    def get_stats(self, name: str) -> Dict[str, Any]:
        values = self._series.get(name, [])
        if not values:
            return {"points": 0}
        return {"points": len(values), "min": min(values), "max": max(values), "avg": sum(values) / len(values), "trend": self.detect_trend(name)}

def run() -> None:
    print("Trend Detector test")
    e = TrendDetector()
    for v in [1, 2, 3, 4, 5, 6, 7, 8]:
        e.add_point("series1", v)
    for v in [10, 9, 8, 7, 6]:
        e.add_point("series2", v)
    for v in [1, 5, 2, 6, 3, 7]:
        e.add_point("series3", v)
    print("  Series1 trend: " + str(e.detect_trend("series1")))
    print("  Series2 trend: " + str(e.detect_trend("series2")))
    print("  Series3 trend: " + str(e.detect_trend("series3")))
    print("  Stats: " + str({k: e.get_stats(k) for k in e._series}))
    print("Trend Detector test complete.")

if __name__ == "__main__":
    run()
