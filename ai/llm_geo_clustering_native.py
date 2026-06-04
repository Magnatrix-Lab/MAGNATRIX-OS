"""Geo Clustering - Spatial clustering for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math
import random

@dataclass
class GeoClustering:
    k: int = 3
    max_iter: int = 100
    
    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def fit(self, points: List[Tuple[float, float]]) -> List[int]:
        if len(points) < self.k: return [0] * len(points)
        # Initialize centroids
        centroids = random.sample(points, self.k)
        assignments = [0] * len(points)
        for _ in range(self.max_iter):
            changed = False
            for i, point in enumerate(points):
                best = min(range(self.k), key=lambda j: self._distance(point, centroids[j]))
                if assignments[i] != best: changed = True
                assignments[i] = best
            for j in range(self.k):
                cluster_points = [points[i] for i in range(len(points)) if assignments[i] == j]
                if cluster_points:
                    centroids[j] = (sum(p[0] for p in cluster_points) / len(cluster_points),
                                    sum(p[1] for p in cluster_points) / len(cluster_points))
            if not changed: break
        return assignments
    
    def stats(self, points: List[Tuple[float, float]]) -> dict:
        assignments = self.fit(points)
        cluster_sizes = [assignments.count(i) for i in range(self.k)]
        return {"k": self.k, "cluster_sizes": cluster_sizes, "points": len(points)}

def run():
    gc = GeoClustering(2)
    points = [(0, 0), (1, 1), (2, 2), (10, 10), (11, 11), (12, 12)]
    assignments = gc.fit(points)
    print("Assignments:", assignments)
    print("Stats:", gc.stats(points))

if __name__ == "__main__": run()
