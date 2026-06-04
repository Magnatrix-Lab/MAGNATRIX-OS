"""Risk Modeler - Value at Risk and risk metrics for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math
import random

class RiskMetric(Enum):
    VAR = auto(); CVAR = auto(); SHARPE = auto()

@dataclass
class RiskModeler:
    confidence: float = 0.95
    
    def calculate_var(self, returns: List[float]) -> float:
        sorted_returns = sorted(returns)
        index = int((1 - self.confidence) * len(sorted_returns))
        return sorted_returns[max(0, index)]
    
    def calculate_cvar(self, returns: List[float]) -> float:
        var = self.calculate_var(returns)
        tail = [r for r in returns if r <= var]
        return sum(tail) / len(tail) if tail else var
    
    def calculate_sharpe(self, returns: List[float], risk_free: float = 0.0) -> float:
        mean = sum(returns) / len(returns)
        std = math.sqrt(sum((r - mean) ** 2 for r in returns) / len(returns))
        return (mean - risk_free) / std if std > 0 else 0.0
    
    def stats(self, returns: List[float]) -> dict:
        return {
            "var_95": round(self.calculate_var(returns), 4),
            "cvar_95": round(self.calculate_cvar(returns), 4),
            "sharpe": round(self.calculate_sharpe(returns), 4)
        }

def run():
    rm = RiskModeler(0.95)
    returns = [0.01, -0.02, 0.03, -0.05, 0.02, -0.01, 0.04, -0.03, 0.01, 0.02]
    print("VaR:", rm.calculate_var(returns))
    print("CVaR:", rm.calculate_cvar(returns))
    print("Sharpe:", rm.calculate_sharpe(returns))
    print("Stats:", rm.stats(returns))

if __name__ == "__main__": run()
