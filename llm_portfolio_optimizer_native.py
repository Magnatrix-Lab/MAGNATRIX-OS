"""Portfolio Optimizer — Markowitz, Sharpe, efficient frontier, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class PortfolioOptimizer:
    returns: List[float] = field(default_factory=list)
    """Expected returns per asset"""
    cov_matrix: List[List[float]] = field(default_factory=list)
    risk_free: float = 0.02

    def portfolio_return(self, weights: List[float]) -> float:
        return sum(w * r for w, r in zip(weights, self.returns))

    def portfolio_risk(self, weights: List[float]) -> float:
        n = len(weights)
        var = 0.0
        for i in range(n):
            for j in range(n):
                var += weights[i] * weights[j] * self.cov_matrix[i][j]
        return math.sqrt(var)

    def sharpe_ratio(self, weights: List[float]) -> float:
        pr = self.portfolio_return(weights)
        risk = self.portfolio_risk(weights)
        return (pr - self.risk_free) / risk if risk > 0 else 0.0

    def equal_weights(self) -> List[float]:
        n = len(self.returns)
        return [1.0 / n] * n

    def random_portfolios(self, n: int = 1000) -> List[Tuple[float, float, List[float]]]:
        import random
        results = []
        for _ in range(n):
            w = [random.random() for _ in self.returns]
            total = sum(w)
            w = [x / total for x in w]
            r = self.portfolio_return(w)
            risk = self.portfolio_risk(w)
            results.append((r, risk, w))
        return sorted(results, key=lambda x: x[1])

    def stats(self, weights: List[float]) -> Dict:
        return {"return": self.portfolio_return(weights), "risk": self.portfolio_risk(weights), "sharpe": self.sharpe_ratio(weights)}

def run():
    po = PortfolioOptimizer([0.1, 0.15, 0.08], [[0.04,0.01,0.005],[0.01,0.09,0.01],[0.005,0.01,0.03]])
    w = po.equal_weights()
    print(po.stats(w))
    print("Best Sharpe:", max(po.random_portfolios(500), key=lambda x: (x[0]-0.02)/x[1] if x[1]>0 else 0))

if __name__ == "__main__":
    run()
