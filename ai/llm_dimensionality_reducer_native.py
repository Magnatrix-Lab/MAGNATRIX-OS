"""LLM Dimensionality Reducer — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class DimensionalityReducer:
    def __init__(self) -> None:
        pass

    def mean_center(self, data: List[List[float]]) -> List[List[float]]:
        if not data or not data[0]:
            return data
        n = len(data)
        dims = len(data[0])
        means = [sum(data[i][d] for i in range(n)) / n for d in range(dims)]
        return [[data[i][d] - means[d] for d in range(dims)] for i in range(n)]

    def covariance_matrix(self, data: List[List[float]]) -> List[List[float]]:
        centered = self.mean_center(data)
        n = len(centered)
        dims = len(centered[0])
        return [[sum(centered[i][d1] * centered[i][d2] for i in range(n)) / (n - 1) for d2 in range(dims)] for d1 in range(dims)]

    def pca(self, data: List[List[float]], n_components: int = 2) -> Dict[str, Any]:
        if not data or not data[0]:
            return {"transformed": [], "explained_variance": [], "components": []}
        centered = self.mean_center(data)
        cov = self.covariance_matrix(data)
        eigenvalues, eigenvectors = self._power_iteration(cov, n_components)
        transformed = [[sum(centered[i][d] * eigenvectors[c][d] for d in range(len(data[0]))) for c in range(n_components)] for i in range(len(data))]
        total_var = sum(eigenvalues)
        explained = [e / total_var if total_var > 0 else 0 for e in eigenvalues]
        return {"transformed": transformed, "explained_variance": explained, "components": eigenvectors}

    def _power_iteration(self, matrix: List[List[float]], k: int, max_iter: int = 100) -> Tuple[List[float], List[List[float]]]:
        n = len(matrix)
        eigenvalues = []
        eigenvectors = []
        A = [row[:] for row in matrix]
        for _ in range(k):
            b = [1.0] * n
            for _ in range(max_iter):
                Ab = [sum(A[i][j] * b[j] for j in range(n)) for i in range(n)]
                norm = math.sqrt(sum(x * x for x in Ab))
                if norm == 0:
                    break
                b = [x / norm for x in Ab]
            eigenvalue = sum(b[i] * sum(A[i][j] * b[j] for j in range(n)) for i in range(n))
            eigenvalues.append(eigenvalue)
            eigenvectors.append(b)
            for i in range(n):
                for j in range(n):
                    A[i][j] -= eigenvalue * b[i] * b[j]
        return eigenvalues, eigenvectors

    def tsvd(self, data: List[List[float]], n_components: int = 2) -> List[List[float]]:
        if not data or not data[0]:
            return []
        centered = self.mean_center(data)
        return [[sum(centered[i][d] for d in range(n_components)) / n_components] for i in range(len(data))]

    def get_stats(self, result: Dict[str, Any]) -> Dict[str, Any]:
        return {"components": len(result.get("components", [])), "explained": result.get("explained_variance", [])}

def run() -> None:
    print("Dimensionality Reducer test")
    e = DimensionalityReducer()
    data = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12], [13, 14, 15]]
    result = e.pca(data, 2)
    print("  Transformed shape: " + str(len(result["transformed"])) + "x" + str(len(result["transformed"][0])))
    print("  Explained variance: " + str([round(v, 3) for v in result["explained_variance"]]))
    print("  Stats: " + str(e.get_stats(result)))
    print("Dimensionality Reducer test complete.")

if __name__ == "__main__":
    run()
