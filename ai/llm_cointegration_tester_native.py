"""Cointegration Tester - Cointegration analysis for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

@dataclass
class CointegrationTester:

    def ols_regression(self, y: List[float], x: List[float]) -> Tuple[float, float]:
        n = len(y)
        mean_x = sum(x) / n; mean_y = sum(y) / n
        ss_xy = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        ss_xx = sum((x[i] - mean_x) ** 2 for i in range(n))
        slope = ss_xy / ss_xx if ss_xx != 0 else 0
        intercept = mean_y - slope * mean_x
        return slope, intercept

    def residuals(self, y: List[float], x: List[float]) -> List[float]:
        slope, intercept = self.ols_regression(y, x)
        return [y[i] - (intercept + slope * x[i]) for i in range(len(y))]

    def adf_statistic(self, series: List[float]) -> float:
        if len(series) < 2: return 0
        diffs = [series[i] - series[i-1] for i in range(1, len(series))]
        mean_diff = sum(diffs) / len(diffs)
        var_diff = sum((d - mean_diff)**2 for d in diffs) / len(diffs)
        return mean_diff / math.sqrt(var_diff / len(diffs)) if var_diff > 0 else 0

    def test(self, y: List[float], x: List[float]) -> Dict:
        resid = self.residuals(y, x)
        adf = self.adf_statistic(resid)
        return {"adf_statistic": round(adf, 4), "cointegrated": adf < -2.5}

    def stats(self, y: List[float], x: List[float]) -> dict:
        return self.test(y, x)

def run():
    ct = CointegrationTester()
    y = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    x = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    print("Test:", ct.test(y, x))
    print("Stats:", ct.stats(y, x))

if __name__ == "__main__": run()
