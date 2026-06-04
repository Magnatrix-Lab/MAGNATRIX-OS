"""Interpolation Engine — linear, spline, Lagrange, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class InterpolationType(Enum):
    LINEAR = auto()
    LAGRANGE = auto()
    NEAREST = auto()

class InterpolationEngine:
    def __init__(self, interp_type: InterpolationType = InterpolationType.LINEAR):
        self.interp_type = interp_type
        self.points: List[Tuple[float, float]] = []

    def fit(self, points: List[Tuple[float, float]]):
        self.points = sorted(points, key=lambda p: p[0])

    def interpolate(self, x: float) -> float:
        if self.interp_type == InterpolationType.LINEAR:
            return self._linear(x)
        elif self.interp_type == InterpolationType.LAGRANGE:
            return self._lagrange(x)
        elif self.interp_type == InterpolationType.NEAREST:
            return self._nearest(x)
        return 0.0

    def _linear(self, x: float) -> float:
        if not self.points:
            return 0.0
        if x <= self.points[0][0]:
            return self.points[0][1]
        if x >= self.points[-1][0]:
            return self.points[-1][1]
        for i in range(len(self.points) - 1):
            x0, y0 = self.points[i]
            x1, y1 = self.points[i + 1]
            if x0 <= x <= x1:
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return self.points[-1][1]

    def _lagrange(self, x: float) -> float:
        n = len(self.points)
        result = 0.0
        for i in range(n):
            xi, yi = self.points[i]
            li = 1.0
            for j in range(n):
                if i != j:
                    xj, _ = self.points[j]
                    li *= (x - xj) / (xi - xj)
            result += yi * li
        return result

    def _nearest(self, x: float) -> float:
        if not self.points:
            return 0.0
        return min(self.points, key=lambda p: abs(p[0] - x))[1]

    def interpolate_batch(self, xs: List[float]) -> List[float]:
        return [self.interpolate(x) for x in xs]

    def stats(self) -> Dict:
        return {"type": self.interp_type.name, "points": len(self.points), "range": (self.points[0][0], self.points[-1][0]) if self.points else None}

def run():
    engine = InterpolationEngine(InterpolationType.LAGRANGE)
    engine.fit([(0, 1), (1, 2), (2, 4), (3, 8)])
    for x in [0.5, 1.5, 2.5]:
        print(f"f({x}) = {engine.interpolate(x)}")
    print(engine.stats())

if __name__ == "__main__":
    run()
