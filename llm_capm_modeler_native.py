"""CAPM Modeler — expected return, beta, SML, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math
import statistics

class CAPMModeler:
    def __init__(self, risk_free_rate: float = 0.03, market_return: float = 0.10):
        self.rf = risk_free_rate
        self.rm = market_return
        self.market_premium = self.rm - self.rf

    def expected_return(self, beta: float) -> float:
        return self.rf + beta * self.market_premium

    def calculate_beta(self, stock_returns: List[float], market_returns: List[float]) -> float:
        if len(stock_returns) != len(market_returns) or len(stock_returns) < 2:
            return 0.0
        stock_mean = statistics.mean(stock_returns)
        market_mean = statistics.mean(market_returns)
        covariance = sum((s - stock_mean) * (m - market_mean) for s, m in zip(stock_returns, market_returns)) / (len(stock_returns) - 1)
        market_variance = sum((m - market_mean) ** 2 for m in market_returns) / (len(market_returns) - 1)
        return covariance / market_variance if market_variance != 0 else 0.0

    def sml(self, betas: List[float]) -> List[Tuple[float, float]]:
        return [(b, self.expected_return(b)) for b in betas]

    def alpha(self, actual_return: float, beta: float) -> float:
        return actual_return - self.expected_return(beta)

    def sharpe_ratio(self, portfolio_return: float, portfolio_std: float) -> float:
        return (portfolio_return - self.rf) / portfolio_std if portfolio_std != 0 else 0.0

    def treynor_ratio(self, portfolio_return: float, beta: float) -> float:
        return (portfolio_return - self.rf) / beta if beta != 0 else 0.0

    def stats(self) -> Dict:
        return {"rf": self.rf, "rm": self.rm, "market_premium": self.market_premium}

def run():
    capm = CAPMModeler(0.03, 0.12)
    print("Expected return (beta=1.2):", capm.expected_return(1.2))
    stock = [0.05, 0.08, -0.02, 0.10, 0.03]
    market = [0.04, 0.06, -0.01, 0.08, 0.02]
    beta = capm.calculate_beta(stock, market)
    print("Beta:", beta)
    print("Alpha:", capm.alpha(0.07, beta))
    print(capm.stats())

if __name__ == "__main__":
    run()
