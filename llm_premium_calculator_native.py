"""Premium Calculator — risk, age, coverage, loading, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class PremiumCalculator:
    base_rate: float = 1000.0
    age: int = 30
    coverage_amount: float = 100000.0
    risk_factor: float = 1.0
    loading: float = 0.2

    def age_adjustment(self) -> float:
        if self.age < 25: return 1.5
        elif self.age < 35: return 1.0
        elif self.age < 50: return 1.3
        elif self.age < 65: return 2.0
        return 3.0

    def coverage_premium(self) -> float:
        return self.coverage_amount * 0.001

    def total_premium(self) -> float:
        return (self.base_rate + self.coverage_premium()) * self.age_adjustment() * self.risk_factor * (1 + self.loading)

    def monthly(self) -> float:
        return self.total_premium() / 12

    def net_premium(self) -> float:
        return self.total_premium() / (1 + self.loading)

    def stats(self) -> Dict:
        return {"annual": round(self.total_premium(), 2), "monthly": round(self.monthly(), 2), "net": round(self.net_premium(), 2)}

def run():
    pc = PremiumCalculator(age=45, coverage_amount=500000, risk_factor=1.2)
    print(pc.stats())

if __name__ == "__main__":
    run()
