"""Histogram Builder — binning, frequency, cumulative, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class HistogramBuilder:
    def __init__(self, bins: int = 10):
        self.bins = bins

    def build(self, data: List[float]) -> Dict:
        if not data:
            return {}
        min_val = min(data)
        max_val = max(data)
        bin_width = (max_val - min_val) / self.bins if max_val != min_val else 1
        counts = [0] * self.bins
        for v in data:
            idx = min(int((v - min_val) / bin_width), self.bins - 1)
            counts[idx] += 1
        edges = [min_val + i * bin_width for i in range(self.bins + 1)]
        cumulative = []
        total = 0
        for c in counts:
            total += c
            cumulative.append(total)
        return {"counts": counts, "edges": edges, "cumulative": cumulative, "total": len(data)}

    def render_ascii(self, data: List[float], width: int = 40) -> str:
        hist = self.build(data)
        counts = hist["counts"]
        if not counts or max(counts) == 0:
            return ""
        max_count = max(counts)
        lines = []
        for i, count in enumerate(counts):
            bar_len = int((count / max_count) * width)
            bar = "#" * bar_len
            edge = hist["edges"][i]
            lines.append(f"{edge:8.2f} |{bar:<{width}}| {count}")
        return "".join(lines)

    def stats(self, data: List[float]) -> Dict:
        return {"bins": self.bins, "mean": sum(data)/len(data) if data else 0}

def run():
    builder = HistogramBuilder(8)
    data = [1, 2, 2, 3, 3, 3, 4, 5, 6, 7, 8, 9, 10]
    print(builder.build(data))
    print(builder.render_ascii(data))
    print(builder.stats(data))

if __name__ == "__main__":
    run()
