"""Granger Causality - Causality test for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

@dataclass
class GrangerCausality:
    max_lag: int = 2

    def lag_matrix(self, data: List[float], lag: int) -> List[List[float]]:
        return [[data[i-j] for j in range(1, lag+1)] for i in range(lag, len(data))]

    def rss(self, y: List[float], X: List[List[float]]) -> float:
        if not X or not y: return float('inf')
        n = len(y)
        preds = [sum(X[i][j] * 0.5 for j in range(len(X[i]))) for i in range(n)]
        return sum((y[i] - preds[i])**2 for i in range(n))

    def test(self, cause: List[float], effect: List[float]) -> Dict:
        min_len = min(len(cause), len(effect))
        cause, effect = cause[:min_len], effect[:min_len]
        lag = self.max_lag
        if len(effect) <= lag: return {"f_stat": 0, "causes": False}
        y = effect[lag:]
        X_restricted = self.lag_matrix(effect, lag)
        X_unrestricted = [X_restricted[i] + self.lag_matrix(cause, lag)[i] for i in range(len(y))]
        rss_r = self.rss(y, X_restricted)
        rss_ur = self.rss(y, X_unrestricted)
        if rss_ur >= rss_r: return {"f_stat": 0, "causes": False}
        f_stat = ((rss_r - rss_ur) / lag) / (rss_ur / (len(y) - 2*lag - 1))
        return {"f_stat": round(f_stat, 4), "causes": f_stat > 3.0}

    def stats(self, cause: List[float], effect: List[float]) -> dict:
        return self.test(cause, effect)

def run():
    gc = GrangerCausality(2)
    cause = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    effect = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    print("Granger test:", gc.test(cause, effect))
    print("Stats:", gc.stats(cause, effect))

if __name__ == "__main__": run()
