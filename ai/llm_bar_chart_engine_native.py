"""LLM Bar Chart Engine — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class BarChartEngine:
    def __init__(self, width: int = 50) -> None:
        self.width = width

    def render(self, data: Dict[str, float], title: str = "", horizontal: bool = True) -> str:
        if not data:
            return ""
        max_val = max(data.values())
        max_label = max(len(k) for k in data.keys())
        lines = ["  " + title if title else "  Bar Chart"]
        lines.append("  " + "=" * (self.width + max_label + 5))
        if horizontal:
            for label, value in sorted(data.items(), key=lambda x: x[1], reverse=True):
                bar_len = int((value / max_val) * self.width) if max_val > 0 else 0
                pct = round(value / max_val * 100, 1) if max_val > 0 else 0.0
                lines.append("  " + label[:max_label].ljust(max_label) + " |" + "=" * bar_len + " " + str(value) + " (" + str(pct) + "%)")
        return "\n".join(lines)

    def render_vertical(self, data: Dict[str, float], height: int = 15) -> str:
        if not data:
            return ""
        max_val = max(data.values())
        labels = list(data.keys())
        values = list(data.values())
        n = len(labels)
        col_width = max(3, self.width // n)
        grid = [[" " for _ in range(n * col_width)] for _ in range(height)]
        for i, val in enumerate(values):
            bar_height = int((val / max_val) * (height - 1)) if max_val > 0 else 0
            for h in range(bar_height):
                row = height - 1 - h
                col = i * col_width + col_width // 2
                if 0 <= row < height and 0 <= col < len(grid[0]):
                    grid[row][col] = "#"
        lines = []
        for r in grid:
            lines.append("  " + "".join(r))
        label_line = "  "
        for label in labels:
            label_line += label[:col_width].center(col_width)
        lines.append(label_line)
        return "\n".join(lines)

    def get_stats(self, data: Dict[str, float]) -> Dict[str, Any]:
        if not data:
            return {"total": 0}
        values = list(data.values())
        return {"total": sum(values), "count": len(data), "average": sum(values) / len(values), "max": max(values), "min": min(values)}

def run() -> None:
    print("Bar Chart Engine test")
    e = BarChartEngine(40)
    data = {"Q1": 120, "Q2": 180, "Q3": 150, "Q4": 220, "Q5": 90}
    print("  Horizontal:\n" + e.render(data, "Revenue by Quarter"))
    print("  Vertical:\n" + e.render_vertical(data, 10))
    print("  Stats: " + str(e.get_stats(data)))
    print("Bar Chart Engine test complete.")

if __name__ == "__main__":
    run()
