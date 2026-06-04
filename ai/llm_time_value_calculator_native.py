"""Time Value Calculator - Present and future value calculations for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

@dataclass
class TimeValueCalculator:
    
    def present_value(self, future_value: float, rate: float, periods: int) -> float:
        return future_value / ((1 + rate) ** periods)
    
    def future_value(self, present_value: float, rate: float, periods: int) -> float:
        return present_value * ((1 + rate) ** periods)
    
    def npv(self, cash_flows: List[float], rate: float) -> float:
        return sum(cf / ((1 + rate) ** i) for i, cf in enumerate(cash_flows))
    
    def irr(self, cash_flows: List[float], guess: float = 0.1) -> float:
        # Simple Newton-Raphson approximation
        rate = guess
        for _ in range(100):
            npv = sum(cf / ((1 + rate) ** i) for i, cf in enumerate(cash_flows))
            derivative = sum(-i * cf / ((1 + rate) ** (i + 1)) for i, cf in enumerate(cash_flows) if i > 0)
            if abs(derivative) < 1e-10: break
            new_rate = rate - npv / derivative
            if abs(new_rate - rate) < 1e-6: break
            rate = new_rate
        return rate
    
    def stats(self, cash_flows: List[float], rate: float) -> dict:
        return {
            "npv": round(self.npv(cash_flows, rate), 4),
            "irr": round(self.irr(cash_flows), 4),
            "cash_flows": len(cash_flows)
        }

def run():
    tvc = TimeValueCalculator()
    cash_flows = [-1000, 300, 400, 400, 300]
    print("NPV at 10%:", round(tvc.npv(cash_flows, 0.10), 4))
    print("IRR:", round(tvc.irr(cash_flows), 4))
    print("Stats:", tvc.stats(cash_flows, 0.10))

if __name__ == "__main__": run()
