"""Chart Generator - ASCII chart generation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

class ChartType(Enum):
    BAR = auto(); LINE = auto(); HISTOGRAM = auto()

@dataclass
class ChartGenerator:
    chart_type: ChartType = ChartType.BAR
    width: int = 60
    height: int = 20
    
    def generate_bar(self, data: List[Tuple[str, float]]) -> str:
        if not data: return ""
        max_val = max(v for _, v in data)
        lines = []
        for label, value in data:
            bar_len = int((value / max_val) * self.width) if max_val > 0 else 0
            lines.append(f"{label:>10} | {'█' * bar_len} {value:.2f}")
        return "\n".join(lines)
    
    def generate_histogram(self, data: List[float], bins: int = 10) -> str:
        if not data: return ""
        min_val, max_val = min(data), max(data)
        bin_width = (max_val - min_val) / bins if max_val > min_val else 1
        counts = [0] * bins
        for v in data:
            idx = min(int((v - min_val) / bin_width), bins - 1)
            counts[idx] += 1
        max_count = max(counts)
        lines = []
        for i, count in enumerate(counts):
            bar_len = int((count / max_count) * self.width) if max_count > 0 else 0
            label = f"{min_val + i * bin_width:.2f}"
            lines.append(f"{label:>10} | {'█' * bar_len} {count}")
        return "\n".join(lines)
    
    def generate(self, data) -> str:
        if self.chart_type == ChartType.BAR and isinstance(data, list) and data and isinstance(data[0], tuple):
            return self.generate_bar(data)
        elif self.chart_type == ChartType.HISTOGRAM and isinstance(data, list):
            return self.generate_histogram(data)
        return ""
    
    def stats(self, data) -> dict:
        return {"chart_type": self.chart_type.name, "width": self.width, "height": self.height}

def run():
    cg = ChartGenerator(ChartType.BAR, 40)
    data = [("A", 10), ("B", 25), ("C", 15), ("D", 30)]
    print(cg.generate(data))
    print("Stats:", cg.stats(data))

if __name__ == "__main__": run()
