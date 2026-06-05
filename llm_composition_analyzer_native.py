"""Composition Analyzer — rule of thirds, golden ratio, balance, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class CompositionAnalyzer:
    width: float = 100.0
    height: float = 100.0

    def rule_of_thirds(self, point: Tuple[float, float]) -> float:
        x_lines = [self.width / 3, 2 * self.width / 3]
        y_lines = [self.height / 3, 2 * self.height / 3]
        dist_x = min(abs(point[0] - xl) for xl in x_lines)
        dist_y = min(abs(point[1] - yl) for yl in y_lines)
        return 1 - (dist_x + dist_y) / (self.width + self.height)

    def golden_ratio(self, a: float, b: float) -> float:
        phi = 1.618
        ratio = max(a, b) / min(a, b) if min(a, b) > 0 else 0
        return 1 - abs(ratio - phi) / phi

    def symmetry_score(self, points: List[Tuple[float, float]]) -> float:
        if not points:
            return 0.0
        center_x = self.width / 2
        diffs = []
        for x, y in points:
            mirror = 2 * center_x - x
            closest = min(abs(mirror - px) for px, py in points)
            diffs.append(closest)
        return 1 - sum(diffs) / (len(diffs) * self.width)

    def balance(self, weights: List[Tuple[float, float, float]]) -> float:
        """(x, y, weight)"""
        if not weights:
            return 0.0
        cx = sum(x * w for x, y, w in weights) / sum(w for _, _, w in weights)
        cy = sum(y * w for x, y, w in weights) / sum(w for _, _, w in weights)
        center_dist = math.sqrt((cx - self.width/2)**2 + (cy - self.height/2)**2)
        return 1 - center_dist / (math.sqrt(self.width**2 + self.height**2) / 2)

    def stats(self, points: List[Tuple[float, float]]) -> Dict:
        return {"symmetry": round(self.symmetry_score(points), 3), "balance": round(self.balance([(x, y, 1) for x, y in points]), 3)}

def run():
    ca = CompositionAnalyzer(300, 200)
    points = [(50, 100), (250, 100), (150, 67), (150, 133)]
    print(ca.stats(points))
    print("Golden ratio:", ca.golden_ratio(100, 161.8))

if __name__ == "__main__":
    run()
