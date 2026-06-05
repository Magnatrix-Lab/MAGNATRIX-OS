"""Plotter — multi-series, legends, axes, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class Series:
    name: str
    x: List[float]
    y: List[float]
    marker: str = "*"

class Plotter:
    def __init__(self, width: int = 60, height: int = 20):
        self.width = width
        self.height = height

    def plot(self, series_list: List[Series]) -> str:
        if not series_list:
            return ""
        all_x = [x for s in series_list for x in s.x]
        all_y = [y for s in series_list for y in s.y]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        rx = max_x - min_x if max_x != min_x else 1
        ry = max_y - min_y if max_y != min_y else 1
        grid = [[" " for _ in range(self.width)] for _ in range(self.height)]
        for s in series_list:
            for x, y in zip(s.x, s.y):
                px = min(int((x - min_x) / rx * (self.width - 1)), self.width - 1)
                py = self.height - 1 - min(int((y - min_y) / ry * (self.height - 1)), self.height - 1)
                grid[py][px] = s.marker
        lines = []
        lines.append(f" {max_y:.2f} +{'-' * (self.width - 2)}+")
        for row in grid:
            lines.append(f"       |{''.join(row)}|")
        lines.append(f" {min_y:.2f} +{'-' * (self.width - 2)}+")
        lines.append(f" {min_x:6.2f} {' ' * (self.width - 12)} {max_x:6.2f}")
        for s in series_list:
            lines.append(f" {s.marker} = {s.name}")
        return "".join(lines)

    def stats(self, series_list: List[Series]) -> Dict:
        return {"series": len(series_list), "total_points": sum(len(s.x) for s in series_list)}

def run():
    plotter = Plotter(50, 15)
    s1 = Series("Sales", list(range(10)), [i * 2 for i in range(10)], "*")
    s2 = Series("Profit", list(range(10)), [i * 1.5 for i in range(10)], "o")
    print(plotter.plot([s1, s2]))
    print(plotter.stats([s1, s2]))

if __name__ == "__main__":
    run()
