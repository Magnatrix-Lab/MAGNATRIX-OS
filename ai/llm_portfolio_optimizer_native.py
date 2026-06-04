"""Portfolio Optimizer - Markowitz portfolio optimization for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math
import random

@dataclass
class PortfolioOptimizer:
    assets: List[str] = field(default_factory=list)
    expected_returns: List[float] = field(default_factory=list)
    cov_matrix: List[List[float]] = field(default_factory=list)
    
    def add_asset(self, name: str, expected_return: float, risks: List[float]) -> None:
        self.assets.append(name)
        self.expected_returns.append(expected_return)
        if not self.cov_matrix:
            self.cov_matrix = [[0.0 for _ in range(len(self.assets))] for _ in range(len(self.assets))]
        for i, r in enumerate(risks):
            self.cov_matrix[len(self.assets)-1][i] = r
            self.cov_matrix[i][len(self.assets)-1] = r
    
    def portfolio_return(self, weights: List[float]) -> float:
        return sum(w * r for w, r in zip(weights, self.expected_returns))
    
    def portfolio_risk(self, weights: List[float]) -> float:
        var = 0.0
        for i in range(len(weights)):
            for j in range(len(weights)):
                var += weights[i] * weights[j] * self.cov_matrix[i][j]
        return math.sqrt(var)
    
    def optimize(self, target_return: float) -> Tuple[float, List[float]]:
        # Simple grid search for small portfolios
        best = None
        best_sharpe = float('-inf')
        for _ in range(1000):
            weights = [random.random() for _ in range(len(self.assets))]
            total = sum(weights)
            weights = [w / total for w in weights]
            ret = self.portfolio_return(weights)
            risk = self.portfolio_risk(weights)
            if abs(ret - target_return) < 0.01 and risk > 0:
                sharpe = ret / risk
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best = weights
        return best_sharpe, best if best else [1.0 / len(self.assets)] * len(self.assets)
    
    def stats(self) -> dict:
        return {"assets": len(self.assets), "expected_returns": [round(r, 4) for r in self.expected_returns]}

def run():
    po = PortfolioOptimizer()
    po.add_asset("A", 0.10, [0.04, 0.02])
    po.add_asset("B", 0.15, [0.02, 0.09])
    sharpe, weights = po.optimize(0.12)
    print(f"Weights: {[round(w, 4) for w in weights]}")
    print(f"Sharpe: {sharpe:.4f}")
    print("Stats:", po.stats())

if __name__ == "__main__": run()
