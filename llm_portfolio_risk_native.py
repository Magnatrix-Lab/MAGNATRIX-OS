"""Portfolio Risk Analyzer — VaR, CVaR, drawdown, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math
import statistics
import random

class PortfolioRiskAnalyzer:
    def __init__(self, confidence: float = 0.95):
        self.confidence = confidence

    def var_historical(self, returns: List[float]) -> float:
        sorted_returns = sorted(returns)
        idx = int((1 - self.confidence) * len(sorted_returns))
        return sorted_returns[max(0, idx)]

    def var_parametric(self, mean: float, std: float) -> float:
        z = -1.645 if self.confidence == 0.95 else (-2.326 if self.confidence == 0.99 else -1.96)
        return mean + z * std

    def cvar(self, returns: List[float]) -> float:
        var = self.var_historical(returns)
        tail = [r for r in returns if r <= var]
        return statistics.mean(tail) if tail else var

    def max_drawdown(self, equity_curve: List[float]) -> float:
        peak = equity_curve[0]
        max_dd = 0.0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd
        return max_dd

    def monte_carlo_var(self, mean: float, std: float, n_sims: int = 10000) -> float:
        sims = [random.gauss(mean, std) for _ in range(n_sims)]
        return self.var_historical(sims)

    def portfolio_std(self, weights: List[float], cov_matrix: List[List[float]]) -> float:
        n = len(weights)
        var = 0.0
        for i in range(n):
            for j in range(n):
                var += weights[i] * weights[j] * cov_matrix[i][j]
        return math.sqrt(var)

    def stats(self) -> Dict:
        return {"confidence": self.confidence, "methods": ["historical", "parametric", "monte_carlo", "cvar"]}

def run():
    risk = PortfolioRiskAnalyzer(0.95)
    returns = [0.02, -0.03, 0.01, -0.05, 0.04, -0.01, 0.03, -0.02, 0.01, -0.04]
    print("VaR:", risk.var_historical(returns))
    print("CVaR:", risk.cvar(returns))
    equity = [100]
    for r in returns:
        equity.append(equity[-1] * (1 + r))
    print("Max Drawdown:", risk.max_drawdown(equity))
    print(risk.stats())

if __name__ == "__main__":
    run()
