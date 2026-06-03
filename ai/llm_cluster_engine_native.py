"""LLM Cluster Engine — Native Python (stdlib only)."""
from __future__ import annotations
import math, random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class ClusterEngine:
    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    def euclidean_distance(self, a: List[float], b: List[float]) -> float:
        return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(len(a))))

    def kmeans(self, data: List[List[float]], k: int, max_iter: int = 100) -> Dict[str, Any]:
        if not data or k > len(data):
            return {"clusters": [], "centroids": [], "assignments": []}
        centroids = self._rng.sample(data, k)
        assignments = [0] * len(data)
        for _ in range(max_iter):
            changed = False
            for i, point in enumerate(data):
                distances = [self.euclidean_distance(point, c) for c in centroids]
                nearest = distances.index(min(distances))
                if assignments[i] != nearest:
                    assignments[i] = nearest
                    changed = True
            if not changed:
                break
            new_centroids = []
            for j in range(k):
                cluster_points = [data[i] for i in range(len(data)) if assignments[i] == j]
                if cluster_points:
                    new_centroids.append([sum(p[d] for p in cluster_points) / len(cluster_points) for d in range(len(data[0]))])
                else:
                    new_centroids.append(centroids[j])
            centroids = new_centroids
        clusters = [[] for _ in range(k)]
        for i, a in enumerate(assignments):
            clusters[a].append(data[i])
        return {"clusters": clusters, "centroids": centroids, "assignments": assignments, "k": k}

    def silhouette_score(self, data: List[List[float]], assignments: List[int]) -> float:
        if len(data) < 2:
            return 0.0
        scores = []
        for i in range(len(data)):
            a = self._avg_distance_to_cluster(data, i, assignments, assignments[i])
            b = min(self._avg_distance_to_cluster(data, i, assignments, j) for j in set(assignments) if j != assignments[i])
            scores.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
        return sum(scores) / len(scores)

    def _avg_distance_to_cluster(self, data: List[List[float]], idx: int, assignments: List[int], cluster_id: int) -> float:
        others = [j for j in range(len(data)) if j != idx and assignments[j] == cluster_id]
        if not others:
            return 0.0
        return sum(self.euclidean_distance(data[idx], data[j]) for j in others) / len(others)

    def get_stats(self, result: Dict[str, Any]) -> Dict[str, Any]:
        clusters = result.get("clusters", [])
        return {"k": result.get("k", 0), "clusters": len(clusters), "sizes": [len(c) for c in clusters]}

def run() -> None:
    print("Cluster Engine test")
    e = ClusterEngine(seed=42)
    data = [[1, 1], [1.5, 2], [2, 1.5], [5, 5], [5.5, 6], [6, 5.5], [10, 10], [10.5, 9.5]]
    result = e.kmeans(data, 3)
    print("  K=3 clusters: " + str([len(c) for c in result["clusters"]]))
    print("  Silhouette: " + str(e.silhouette_score(data, result["assignments"])))
    print("  Stats: " + str(e.get_stats(result)))
    print("Cluster Engine test complete.")

if __name__ == "__main__":
    run()
