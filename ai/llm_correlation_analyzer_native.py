"""LLM Correlation Analyzer — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class CorrelationAnalyzer:
    def __init__(self) -> None:
        pass

    def pearson(self, x: List[float], y: List[float]) -> float:
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        den_x = sum((xi - mean_x) ** 2 for xi in x)
        den_y = sum((yi - mean_y) ** 2 for yi in y)
        if den_x == 0 or den_y == 0:
            return 0.0
        return num / math.sqrt(den_x * den_y)

    def spearman(self, x: List[float], y: List[float]) -> float:
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        n = len(x)
        rank_x = self._rank(x)
        rank_y = self._rank(y)
        d_squared = sum((rank_x[i] - rank_y[i]) ** 2 for i in range(n))
        return 1 - (6 * d_squared) / (n * (n * n - 1))

    def _rank(self, data: List[float]) -> List[float]:
        sorted_vals = sorted((v, i) for i, v in enumerate(data))
        ranks = [0.0] * len(data)
        i = 0
        while i < len(sorted_vals):
            j = i
            while j < len(sorted_vals) and sorted_vals[j][0] == sorted_vals[i][0]:
                j += 1
            rank = (i + 1 + j) / 2.0
            for k in range(i, j):
                ranks[sorted_vals[k][1]] = rank
            i = j
        return ranks

    def covariance(self, x: List[float], y: List[float]) -> float:
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        return sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / (n - 1)

    def correlation_matrix(self, data: List[List[float]]) -> List[List[float]]:
        n = len(data)
        return [[self.pearson(data[i], data[j]) for j in range(n)] for i in range(n)]

    def get_stats(self, x: List[float], y: List[float]) -> Dict[str, Any]:
        return {"pearson": self.pearson(x, y), "spearman": self.spearman(x, y), "covariance": self.covariance(x, y)}

def run() -> None:
    print("Correlation Analyzer test")
    e = CorrelationAnalyzer()
    x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    y = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
    z = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    print("  Pearson x,y: " + str(e.pearson(x, y)))
    print("  Pearson x,z: " + str(e.pearson(x, z)))
    print("  Spearman x,y: " + str(e.spearman(x, y)))
    print("  Stats: " + str(e.get_stats(x, y)))
    print("Correlation Analyzer test complete.")

if __name__ == "__main__":
    run()
