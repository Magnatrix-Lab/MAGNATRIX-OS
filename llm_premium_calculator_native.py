"""Premium Calculator — actuarial, risk class, loading, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class PremiumCalculator:
    base_rate: float = 1000.0
    age_factor: float = 1.0
    risk_factor: float = 1.0
    loading: float = 0.15

    def calculate(self) -> float:
        return self.base_rate * self.age_factor * self.risk_factor * (1 + self.loading)

    def risk_adjusted(self, claims_history: int, credit_score: int) -> float:
        risk_mult = 1.0 + claims_history * 0.1 - (credit_score - 700) / 1000
        return self.base_rate * self.age_factor * max(0.5, risk_mult) * (1 + self.loading)

    def term_premium(self, years: int) -> float:
        annual = self.calculate()
        return annual * years * (1 - 0.02 * (years - 1))

    def earned_premium(self, elapsed_months: int, term_months: int = 12) -> float:
        return self.calculate() * (elapsed_months / term_months)

    def stats(self) -> Dict:
        return {"base": self.base_rate, "premium": round(self.calculate(), 2), "term_3yr": round(self.term_premium(3), 2)}

def run():
    pc = PremiumCalculator(base_rate=2000, age_factor=1.2, risk_factor=1.5)
    print(pc.stats())
    print("Risk adjusted:", pc.risk_adjusted(2, 720))

if __name__ == "__main__":
    run()
