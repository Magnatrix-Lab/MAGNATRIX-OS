"""LLM Plot Engine — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class PlotEngine:
    def __init__(self, width: int = 60, height: int = 20) -> None:
        self.width = width
        self.height = height
        self._plots: List[Dict[str, Any]] = []

    def plot_function(self, fn: callable, x_min: float, x_max: float, title: str = "") -> str:
        step = (x_max - x_min) / (self.width - 1)
        points = []
        for i in range(self.width):
            x = x_min + i * step
            try:
                y = fn(x)
                points.append((x, y))
            except Exception:
                points.append((x, None))
        y_vals = [p[1] for p in points if p[1] is not None]
        if not y_vals:
            return ""
        y_min, y_max = min(y_vals), max(y_vals)
        grid = [[" " for _ in range(self.width)] for _ in range(self.height)]
        for i, (x, y) in enumerate(points):
            if y is not None:
                row = int((y - y_min) / (y_max - y_min) * (self.height - 1)) if y_max != y_min else 0
                row = self.height - 1 - row
                grid[row][i] = "*"
        lines = ["  " + title if title else "  Plot"]
        for r in grid:
            lines.append("  " + "".join(r))
        lines.append("  " + " " * 5 + str(round(x_min, 1)).ljust(20) + str(round(x_max, 1)))
        return "\n".join(lines)

    def plot_series(self, series: List[Tuple[float, float]], title: str = "") -> str:
        if not series:
            return ""
        x_vals = [p[0] for p in series]
        y_vals = [p[1] for p in series]
        x_min, x_max = min(x_vals), max(x_vals)
        y_min, y_max = min(y_vals), max(y_vals)
        grid = [[" " for _ in range(self.width)] for _ in range(self.height)]
        for x, y in series:
            col = int((x - x_min) / (x_max - x_min) * (self.width - 1)) if x_max != x_min else 0
            row = int((y - y_min) / (y_max - y_min) * (self.height - 1)) if y_max != y_min else 0
            row = self.height - 1 - row
            grid[row][col] = "*"
        lines = ["  " + title if title else "  Series"]
        for r in grid:
            lines.append("  " + "".join(r))
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        return {"plots": len(self._plots), "width": self.width, "height": self.height}

def run() -> None:
    print("Plot Engine test")
    e = PlotEngine(40, 15)
    print("  Sine wave:\n" + e.plot_function(lambda x: math.sin(x), 0, 4 * math.pi, "sin(x)"))
    series = [(i, i**2) for i in range(10)]
    print("  Square series:\n" + e.plot_series(series, "x^2"))
    print("  Stats: " + str(e.get_stats()))
    print("Plot Engine test complete.")

if __name__ == "__main__":
    run()
