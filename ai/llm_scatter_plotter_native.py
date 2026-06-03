"""LLM Scatter Plotter — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class ScatterPlotter:
    def __init__(self, width: int = 50, height: int = 20) -> None:
        self.width = width
        self.height = height

    def plot(self, points: List[Tuple[float, float]], title: str = "", x_label: str = "", y_label: str = "") -> str:
        if not points:
            return ""
        x_vals = [p[0] for p in points]
        y_vals = [p[1] for p in points]
        x_min, x_max = min(x_vals), max(x_vals)
        y_min, y_max = min(y_vals), max(y_vals)
        x_range = max(x_max - x_min, 1e-10)
        y_range = max(y_max - y_min, 1e-10)
        grid = [[" " for _ in range(self.width)] for _ in range(self.height)]
        for x, y in points:
            col = int((x - x_min) / x_range * (self.width - 1))
            row = int((y - y_min) / y_range * (self.height - 1))
            row = self.height - 1 - row
            grid[row][col] = "*"
        lines = ["  " + title if title else "  Scatter Plot"]
        for r in grid:
            lines.append("  " + "".join(r))
        lines.append("  " + x_label.center(self.width))
        return "\n".join(lines)

    def plot_with_groups(self, groups: Dict[str, List[Tuple[float, float]]], title: str = "") -> str:
        all_points = []
        for pts in groups.values():
            all_points.extend(pts)
        if not all_points:
            return ""
        x_vals = [p[0] for p in all_points]
        y_vals = [p[1] for p in all_points]
        x_min, x_max = min(x_vals), max(x_vals)
        y_min, y_max = min(y_vals), max(y_vals)
        x_range = max(x_max - x_min, 1e-10)
        y_range = max(y_max - y_min, 1e-10)
        symbols = ["*", "o", "x", "+", "#", "@", "&", "%", "=", "-"]
        grid = [[" " for _ in range(self.width)] for _ in range(self.height)]
        for i, (group_name, pts) in enumerate(groups.items()):
            sym = symbols[i % len(symbols)]
            for x, y in pts:
                col = int((x - x_min) / x_range * (self.width - 1))
                row = int((y - y_min) / y_range * (self.height - 1))
                row = self.height - 1 - row
                grid[row][col] = sym
        lines = ["  " + title if title else "  Multi-Group Scatter"]
        for group_name, _ in groups.items():
            sym = symbols[list(groups.keys()).index(group_name) % len(symbols)]
            lines.append("  " + sym + " " + group_name)
        lines.append("")
        for r in grid:
            lines.append("  " + "".join(r))
        return "\n".join(lines)

    def get_stats(self, points: List[Tuple[float, float]]) -> Dict[str, Any]:
        if not points:
            return {"count": 0}
        x_vals = [p[0] for p in points]
        y_vals = [p[1] for p in points]
        x_mean = sum(x_vals) / len(x_vals)
        y_mean = sum(y_vals) / len(y_vals)
        return {"count": len(points), "x_mean": x_mean, "y_mean": y_mean, "x_range": max(x_vals) - min(x_vals), "y_range": max(y_vals) - min(y_vals)}

def run() -> None:
    print("Scatter Plotter test")
    e = ScatterPlotter(40, 12)
    points = [(1, 2), (2, 3), (3, 5), (4, 4), (5, 7), (6, 6), (7, 8), (8, 9)]
    print("  Plot:\n" + e.plot(points, "Sample Data"))
    groups = {"A": [(1, 2), (2, 3), (3, 4)], "B": [(5, 6), (6, 7), (7, 8)]}
    print("  Grouped:\n" + e.plot_with_groups(groups, "Groups"))
    print("  Stats: " + str(e.get_stats(points)))
    print("Scatter Plotter test complete.")

if __name__ == "__main__":
    run()
