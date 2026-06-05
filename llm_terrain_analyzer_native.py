"""Terrain Analyzer — slope, cover, mobility, line of sight, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class TerrainAnalyzer:
    elevation_grid: List[List[float]] = field(default_factory=list)
    cell_size: float = 10.0

    def slope(self, row: int, col: int) -> float:
        if not self.elevation_grid or row <= 0 or col <= 0 or row >= len(self.elevation_grid)-1 or col >= len(self.elevation_grid[0])-1:
            return 0.0
        dzdx = (self.elevation_grid[row][col+1] - self.elevation_grid[row][col-1]) / (2 * self.cell_size)
        dzdy = (self.elevation_grid[row+1][col] - self.elevation_grid[row-1][col]) / (2 * self.cell_size)
        return math.degrees(math.atan(math.sqrt(dzdx**2 + dzdy**2)))

    def mobility_score(self, row: int, col: int) -> float:
        s = self.slope(row, col)
        return max(0, 1 - s / 45)

    def line_of_sight(self, r1: Tuple[int, int], r2: Tuple[int, int]) -> bool:
        x0, y0 = r1
        x1, y1 = r2
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        h0 = self.elevation_grid[x0][y0] if x0 < len(self.elevation_grid) and y0 < len(self.elevation_grid[0]) else 0
        h1 = self.elevation_grid[x1][y1] if x1 < len(self.elevation_grid) and y1 < len(self.elevation_grid[0]) else 0
        while True:
            if x0 == x1 and y0 == y1:
                break
            if 0 <= x0 < len(self.elevation_grid) and 0 <= y0 < len(self.elevation_grid[0]):
                h = self.elevation_grid[x0][y0]
                t = math.sqrt((x0-r1[0])**2 + (y0-r1[1])**2) / math.sqrt(dx**2 + dy**2) if dx+dy > 0 else 0
                expected = h0 + t * (h1 - h0)
                if h > expected + 1:
                    return False
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
        return True

    def stats(self) -> Dict:
        flat = [v for row in self.elevation_grid for v in row]
        return {"cells": len(flat), "min_elev": min(flat) if flat else 0, "max_elev": max(flat) if flat else 0}

def run():
    ta = TerrainAnalyzer([[10,10,10,10],[10,15,20,10],[10,12,18,10]], cell_size=10)
    print(ta.stats())
    print("Slope(1,1):", ta.slope(1,1))
    print("LOS (0,0)->(2,3):", ta.line_of_sight((0,0), (2,3)))

if __name__ == "__main__":
    run()
