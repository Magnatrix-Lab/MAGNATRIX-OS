"""LLM Chart Generator — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class ChartType(Enum):
    LINE = auto()
    BAR = auto()
    PIE = auto()
    SCATTER = auto()
    AREA = auto()
    HISTOGRAM = auto()

@dataclass
class DataPoint:
    label: str
    value: float
    color: str = "#000000"
    metadata: Dict[str, Any] = field(default_factory=dict)

class ChartGenerator:
    def __init__(self) -> None:
        self._charts: List[Dict[str, Any]] = []

    def create_line_chart(self, data: List[DataPoint], title: str = "", width: int = 60, height: int = 10) -> str:
        if not data:
            return ""
        max_val = max(d.value for d in data)
        lines = ["  " + title, "  " + "-" * width]
        for point in data:
            bar_len = int((point.value / max_val) * (width - 5)) if max_val > 0 else 0
            lines.append("  " + point.label[:10].ljust(10) + " " + "#" * bar_len + " " + str(point.value))
        return "\n".join(lines)

    def create_bar_chart(self, data: List[DataPoint], title: str = "", width: int = 40) -> str:
        if not data:
            return ""
        max_val = max(d.value for d in data)
        lines = ["  " + title, "  " + "=" * width]
        for point in data:
            bar_len = int((point.value / max_val) * width) if max_val > 0 else 0
            lines.append("  " + point.label[:15].ljust(15) + " |" + "=" * bar_len + " " + str(point.value))
        return "\n".join(lines)

    def create_pie_chart(self, data: List[DataPoint], title: str = "") -> str:
        if not data:
            return ""
        total = sum(d.value for d in data)
        lines = ["  " + title, "  " + "-" * 40]
        for point in data:
            pct = (point.value / total * 100) if total > 0 else 0
            bar = int(pct / 5)
            lines.append("  " + point.label[:15].ljust(15) + " " + "=" * bar + " " + str(round(pct, 1)) + "%")
        return "\n".join(lines)

    def create_scatter_plot(self, data: List[Tuple[float, float]], title: str = "", width: int = 40, height: int = 20) -> str:
        if not data:
            return ""
        x_vals = [d[0] for d in data]
        y_vals = [d[1] for d in data]
        min_x, max_x = min(x_vals), max(x_vals)
        min_y, max_y = min(y_vals), max(y_vals)
        grid = [[" " for _ in range(width)] for _ in range(height)]
        for x, y in data:
            col = int((x - min_x) / (max_x - min_x) * (width - 1)) if max_x != min_x else 0
            row = int((y - min_y) / (max_y - min_y) * (height - 1)) if max_y != min_y else 0
            row = height - 1 - row
            grid[row][col] = "*"
        lines = ["  " + title]
        for r in grid:
            lines.append("  " + "".join(r))
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        return {"charts": len(self._charts)}

def run() -> None:
    print("Chart Generator test")
    e = ChartGenerator()
    data = [DataPoint("A", 30, "#FF0000"), DataPoint("B", 50, "#00FF00"), DataPoint("C", 20, "#0000FF"), DataPoint("D", 40, "#FFFF00")]
    print("  Line Chart:\n" + e.create_line_chart(data, "Sales"))
    print("  Bar Chart:\n" + e.create_bar_chart(data, "Revenue"))
    print("  Pie Chart:\n" + e.create_pie_chart(data, "Share"))
    scatter = [(1, 2), (3, 5), (5, 3), (7, 8), (9, 6)]
    print("  Scatter Plot:\n" + e.create_scatter_plot(scatter, "Correlation"))
    print("  Stats: " + str(e.get_stats()))
    print("Chart Generator test complete.")

if __name__ == "__main__":
    run()
