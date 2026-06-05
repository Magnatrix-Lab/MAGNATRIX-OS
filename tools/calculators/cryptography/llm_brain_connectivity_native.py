"""Brain Connectivity — correlation matrix, graph metrics, FC/DFC, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class BrainConnectivity:
    regions: List[str] = field(default_factory=list)
    time_series: Dict[str, List[float]] = field(default_factory=dict)

    def correlation_matrix(self) -> List[List[float]]:
        n = len(self.regions)
        mat = [[0.0]*n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                mat[i][j] = self._pearson(self.time_series[self.regions[i]], self.time_series[self.regions[j]])
        return mat

    def _pearson(self, a: List[float], b: List[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        ma, mb = sum(a)/len(a), sum(b)/len(b)
        num = sum((x-ma)*(y-mb) for x,y in zip(a,b))
        den = math.sqrt(sum((x-ma)**2 for x in a) * sum((y-mb)**2 for y in b))
        return num / den if den > 0 else 0.0

    def clustering_coefficient(self, mat: List[List[float]], threshold: float = 0.5) -> float:
        n = len(mat)
        if n < 3:
            return 0.0
        cc = 0.0
        for i in range(n):
            neighbors = [j for j in range(n) if j != i and mat[i][j] > threshold]
            if len(neighbors) < 2:
                continue
            triangles = sum(1 for j in neighbors for k in neighbors if j < k and mat[j][k] > threshold)
            possible = len(neighbors) * (len(neighbors) - 1) / 2
            if possible > 0:
                cc += triangles / possible
        return cc / n

    def stats(self) -> Dict:
        return {"regions": len(self.regions)}

def run():
    bc = BrainConnectivity(["A","B","C"], {"A":[1,2,3,4],"B":[2,3,4,5],"C":[5,4,3,2]})
    mat = bc.correlation_matrix()
    print("Corr:", mat)
    print("CC:", bc.clustering_coefficient(mat))
    print(bc.stats())

if __name__ == "__main__":
    run()
