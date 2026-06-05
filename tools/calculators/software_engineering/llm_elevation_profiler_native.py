"""Elevation Profiler — DEM analysis, slope, aspect, hillshade, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class ElevationProfile:
    dem: List[List[float]] = field(default_factory=list)
    cell_size: float = 30.0

    def slope(self, row: int, col: int) -> float:
        if not self.dem or row <= 0 or col <= 0 or row >= len(self.dem)-1 or col >= len(self.dem[0])-1:
            return 0.0
        dzdx = (self.dem[row][col+1] - self.dem[row][col-1]) / (2 * self.cell_size)
        dzdy = (self.dem[row+1][col] - self.dem[row-1][col]) / (2 * self.cell_size)
        return math.degrees(math.atan(math.sqrt(dzdx**2 + dzdy**2)))

    def aspect(self, row: int, col: int) -> float:
        if not self.dem or row <= 0 or col <= 0 or row >= len(self.dem)-1 or col >= len(self.dem[0])-1:
            return -1.0
        dzdx = (self.dem[row][col+1] - self.dem[row][col-1]) / (2 * self.cell_size)
        dzdy = (self.dem[row+1][col] - self.dem[row-1][col]) / (2 * self.cell_size)
        if dzdx == 0 and dzdy == 0:
            return -1.0
        aspect = math.degrees(math.atan2(dzdy, -dzdx))
        if aspect < 0:
            aspect += 360
        return aspect

    def hillshade(self, azimuth: float = 315, altitude: float = 45) -> List[List[float]]:
        if not self.dem:
            return []
        az = math.radians(azimuth)
        alt = math.radians(altitude)
        rows, cols = len(self.dem), len(self.dem[0])
        result = [[0.0]*cols for _ in range(rows)]
        for r in range(1, rows-1):
            for c in range(1, cols-1):
                dzdx = (self.dem[r][c+1] - self.dem[r][c-1]) / (2 * self.cell_size)
                dzdy = (self.dem[r+1][c] - self.dem[r-1][c]) / (2 * self.cell_size)
                slope = math.atan(math.sqrt(dzdx**2 + dzdy**2))
                aspect = math.atan2(dzdy, -dzdx) - az
                result[r][c] = max(0, 255 * (math.cos(alt) * math.cos(slope) + math.sin(alt) * math.sin(slope) * math.cos(aspect)))
        return result

    def profile(self, line: List[Tuple[int, int]]) -> List[float]:
        return [self.dem[r][c] for r, c in line if 0 <= r < len(self.dem) and 0 <= c < len(self.dem[0])]

    def stats(self) -> Dict:
        if not self.dem:
            return {}
        flat = [v for row in self.dem for v in row]
        return {"rows": len(self.dem), "cols": len(self.dem[0]), "min": min(flat), "max": max(flat), "mean": sum(flat)/len(flat)}

def run():
    ep = ElevationProfile([[10,10,10,10],[10,15,20,10],[10,12,18,10],[10,10,10,10]], cell_size=10)
    print("Slope(1,1):", ep.slope(1,1))
    print("Aspect(1,1):", ep.aspect(1,1))
    print(ep.stats())

if __name__ == "__main__":
    run()
