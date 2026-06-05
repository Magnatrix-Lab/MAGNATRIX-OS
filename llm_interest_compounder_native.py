"""Interest Compounder — simple, compound, continuous, APY, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class InterestCompounder:
    principal: float = 1000.0
    rate: float = 0.05
    years: float = 10.0

    def simple_interest(self) -> float:
        return self.principal * (1 + self.rate * self.years)

    def compound_annual(self, n: int = 1) -> float:
        return self.principal * (1 + self.rate / n) ** (n * self.years)

    def compound_continuous(self) -> float:
        return self.principal * math.exp(self.rate * self.years)

    def apy(self, n: int = 12) -> float:
        return (1 + self.rate / n) ** n - 1

    def effective_rate(self, inflation: float = 0.02) -> float:
        return (1 + self.rate) / (1 + inflation) - 1

    def doubling_time(self) -> float:
        if self.rate <= 0:
            return float('inf')
        return math.log(2) / math.log(1 + self.rate)

    def rule_of_72(self) -> float:
        return 72 / (self.rate * 100) if self.rate > 0 else float('inf')

    def stats(self) -> Dict:
        return {"simple": round(self.simple_interest(), 2), "compound_annual": round(self.compound_annual(), 2), "continuous": round(self.compound_continuous(), 2), "apy": round(self.apy(), 4)}

def run():
    ic = InterestCompounder(principal=5000, rate=0.07, years=20)
    print(ic.stats())
    print("Doubling time:", ic.doubling_time())
    print("Rule of 72:", ic.rule_of_72())

if __name__ == "__main__":
    run()
