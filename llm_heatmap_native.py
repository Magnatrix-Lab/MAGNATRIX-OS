"""Heatmap — 2D matrix rendering, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class Heatmap:
    def __init__(self, width: int = 40, height: int = 20):
        self.width = width
        self.height = height
        self.chars = " .:-=+*#%@"

    def render(self, matrix: List[List[float]]) -> str:
        if not matrix or not matrix[0]:
            return ""
        min_val = min(min(row) for row in matrix)
        max_val = max(max(row) for row in matrix)
        range_val = max_val - min_val if max_val != min_val else 1
        lines = []
        for row in matrix:
            line = ""
            for val in row:
                idx = int((val - min_val) / range_val * (len(self.chars) - 1))
                line += self.chars[idx]
            lines.append(line)
        return "".join(lines)

    def stats(self, matrix: List[List[float]]) -> Dict:
        if not matrix:
            return {}
        flat = [v for row in matrix for v in row]
        return {"rows": len(matrix), "cols": len(matrix[0]), "min": min(flat), "max": max(flat)}

def run():
    heatmap = Heatmap(20, 10)
    matrix = [[i * j for j in range(20)] for i in range(10)]
    print(heatmap.render(matrix))
    print(heatmap.stats(matrix))

if __name__ == "__main__":
    run()
