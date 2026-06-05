"""Native stdlib module: Tea Pricing Calculator
Calculates tea leaf costs, grade premiums, and retail pricing.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class TeaPricingCalculator:
    base_cost_per_kg: float
    grade: str  # estate, premium, tgy, special, reserve
    origin_premium_pct: float = 0.0
    packaging_cost_per_kg: float = 5.0
    labor_cost_per_kg: float = 10.0
    overhead_pct: float = 20.0
    profit_margin_pct: float = 40.0

    _GRADE_MULTIPLIERS = {
        "estate": 1.0, "premium": 1.5, "tgy": 2.0, "special": 3.0, "reserve": 5.0,
    }

    def graded_cost_per_kg(self) -> float:
        return self.base_cost_per_kg * self._GRADE_MULTIPLIERS.get(self.grade, 1.0)

    def origin_adjusted_cost(self) -> float:
        return self.graded_cost_per_kg() * (1 + self.origin_premium_pct / 100)

    def total_cost_per_kg(self) -> float:
        return self.origin_adjusted_cost() + self.packaging_cost_per_kg + self.labor_cost_per_kg

    def wholesale_price_per_kg(self) -> float:
        return self.total_cost_per_kg() * (1 + self.overhead_pct / 100) * (1 + self.profit_margin_pct / 100)

    def retail_price_per_kg(self, markup: float = 2.0) -> float:
        return self.wholesale_price_per_kg() * markup

    def price_per_50g(self) -> float:
        return self.retail_price_per_kg() / 20

    def price_per_100g(self) -> float:
        return self.retail_price_per_kg() / 10

    def stats(self) -> Dict:
        return {
            "grade": self.grade,
            "base_cost_per_kg": self.base_cost_per_kg,
            "graded_cost_per_kg": round(self.graded_cost_per_kg(), 2),
            "total_cost_per_kg": round(self.total_cost_per_kg(), 2),
            "wholesale_price_per_kg": round(self.wholesale_price_per_kg(), 2),
            "retail_price_per_kg": round(self.retail_price_per_kg(), 2),
            "price_per_50g": round(self.price_per_50g(), 2),
            "price_per_100g": round(self.price_per_100g(), 2),
        }

def run():
    tpc = TeaPricingCalculator(base_cost_per_kg=50, grade="premium", origin_premium_pct=20, packaging_cost_per_kg=8, labor_cost_per_kg=15)
    print(tpc.stats())

if __name__ == "__main__":
    run()
