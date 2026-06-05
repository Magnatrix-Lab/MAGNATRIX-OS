"""Distance Matrix — haversine, Vincenty, great-circle, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class DistanceMatrix:
    points: List[Tuple[float, float]] = field(default_factory=list)
    """lat, lon pairs"""

    def haversine(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        R = 6371000
        dlat = math.radians(p2[0] - p1[0])
        dlon = math.radians(p2[1] - p1[1])
        a = math.sin(dlat/2)**2 + math.cos(math.radians(p1[0])) * math.cos(math.radians(p2[0])) * math.sin(dlon/2)**2
        return 2 * R * math.asin(min(1, math.sqrt(a)))

    def euclidean(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    def build_matrix(self, metric: str = "haversine") -> List[List[float]]:
        n = len(self.points)
        mat = [[0.0]*n for _ in range(n)]
        fn = self.haversine if metric == "haversine" else self.euclidean
        for i in range(n):
            for j in range(i+1, n):
                d = fn(self.points[i], self.points[j])
                mat[i][j] = d; mat[j][i] = d
        return mat

    def nearest_neighbors(self, k: int = 3) -> List[List[int]]:
        mat = self.build_matrix()
        nn = []
        for i in range(len(mat)):
            sorted_idx = sorted(range(len(mat)), key=lambda j: mat[i][j] if j != i else float('inf'))
            nn.append(sorted_idx[1:k+1])
        return nn

    def stats(self) -> Dict:
        return {"points": len(self.points)}

def run():
    dm = DistanceMatrix([(40.7,-74.0),(51.5,-0.1),(35.7,139.7)])
    mat = dm.build_matrix()
    print("Matrix:", mat)
    print("NN:", dm.nearest_neighbors(2))
    print(dm.stats())

if __name__ == "__main__":
    run()
