"""Risk Calculator — VaR, CVaR, drawdown, beta, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class RiskCalculator:
    returns: List[float] = field(default_factory=list)

    def mean_return(self) -> float:
        return sum(self.returns) / len(self.returns) if self.returns else 0.0

    def volatility(self) -> float:
        if not self.returns:
            return 0.0
        m = self.mean_return()
        return math.sqrt(sum((r - m)**2 for r in self.returns) / len(self.returns))

    def var(self, confidence: float = 0.95) -> float:
        if not self.returns:
            return 0.0
        sorted_r = sorted(self.returns)
        idx = int((1 - confidence) * len(sorted_r))
        return sorted_r[idx]

    def cvar(self, confidence: float = 0.95) -> float:
        if not self.returns:
            return 0.0
        threshold = self.var(confidence)
        tails = [r for r in self.returns if r <= threshold]
        return sum(tails) / len(tails) if tails else 0.0

    def max_drawdown(self, values: List[float]) -> float:
        if not values:
            return 0.0
        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
        return max_dd

    def beta(self, market_returns: List[float]) -> float:
        if len(self.returns) != len(market_returns) or not self.returns:
            return 0.0
        m = sum(self.returns) / len(self.returns)
        mm = sum(market_returns) / len(market_returns)
        cov = sum((a - m) * (b - mm) for a, b in zip(self.returns, market_returns)) / len(self.returns)
        mvar = sum((b - mm)**2 for b in market_returns) / len(market_returns)
        return cov / mvar if mvar > 0 else 0.0

    def stats(self) -> Dict:
        return {"volatility": self.volatility(), "VaR_95": self.var(), "CVaR_95": self.cvar(), "max_drawdown": self.max_drawdown([1+r for r in self.returns])}

def run():
    rc = RiskCalculator([-0.02, 0.03, -0.01, 0.05, -0.04, 0.02])
    print(rc.stats())
    print("Beta:", rc.beta([0.01, 0.02, -0.01, 0.03, -0.02, 0.01]))

if __name__ == "__main__":
    run()
