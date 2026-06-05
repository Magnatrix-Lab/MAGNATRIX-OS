"""Scatter Plot — 2D point rendering, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class ScatterPlot:
    def __init__(self, width: int = 40, height: int = 20):
        self.width = width
        self.height = height

    def render(self, points: List[Tuple[float, float]]) -> str:
        if not points:
            return ""
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        range_x = max_x - min_x if max_x != min_x else 1
        range_y = max_y - min_y if max_y != min_y else 1
        grid = [[" " for _ in range(self.width)] for _ in range(self.height)]
        for x, y in points:
            px = min(int((x - min_x) / range_x * (self.width - 1)), self.width - 1)
            py = self.height - 1 - min(int((y - min_y) / range_y * (self.height - 1)), self.height - 1)
            grid[py][px] = "*"
        return "".join("".join(row) for row in grid)

    def stats(self, points: List[Tuple[float, float]]) -> Dict:
        if not points:
            return {}
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return {"count": len(points), "x_range": (min(xs), max(xs)), "y_range": (min(ys), max(ys))}

def run():
    plot = ScatterPlot(30, 15)
    points = [(i, i**2) for i in range(10)]
    print(plot.render(points))
    print(plot.stats(points))

if __name__ == "__main__":
    run()
