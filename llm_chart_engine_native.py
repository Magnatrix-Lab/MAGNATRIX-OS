"""Chart Engine — bar, line, pie charts, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class ChartType(Enum):
    BAR = auto()
    LINE = auto()
    PIE = auto()
    SCATTER = auto()

@dataclass
class ChartData:
    labels: List[str]
    values: List[float]
    series_name: str = "Series"

class ChartEngine:
    def __init__(self, width: int = 60, height: int = 20):
        self.width = width
        self.height = height

    def render_bar(self, data: ChartData) -> str:
        if not data.values:
            return ""
        max_val = max(data.values)
        lines = []
        for label, value in zip(data.labels, data.values):
            bar_len = int((value / max_val) * self.width) if max_val else 0
            bar = "#" * bar_len
            lines.append(f"{label:10} |{bar:<{self.width}}| {value:.1f}")
        return "".join(lines)

    def render_line(self, data: ChartData) -> str:
        if not data.values:
            return ""
        max_val = max(data.values)
        min_val = min(data.values)
        range_val = max_val - min_val if max_val != min_val else 1
        grid = [[" " for _ in range(len(data.values))] for _ in range(self.height)]
        for i, v in enumerate(data.values):
            row = self.height - 1 - int(((v - min_val) / range_val) * (self.height - 1))
            grid[row][i] = "*"
        return "".join("".join(row) for row in grid)

    def render_pie(self, data: ChartData) -> str:
        if not data.values or sum(data.values) == 0:
            return ""
        total = sum(data.values)
        slices = []
        for label, value in zip(data.labels, data.values):
            pct = value / total * 100
            slices.append(f"{label}: {pct:.1f}%")
        return "".join(slices)

    def stats(self, data: ChartData) -> Dict:
        return {"type": "chart", "points": len(data.values), "max": max(data.values) if data.values else 0}

def run():
    engine = ChartEngine(40, 10)
    data = ChartData(["A", "B", "C", "D"], [10, 25, 15, 30])
    print(engine.render_bar(data))
    print(engine.render_line(data))
    print(engine.render_pie(data))
    print(engine.stats(data))

if __name__ == "__main__":
    run()
