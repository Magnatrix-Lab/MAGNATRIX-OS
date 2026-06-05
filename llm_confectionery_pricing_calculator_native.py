"""Native stdlib module: Confectionery Pricing Calculator
Calculates ingredient costs, packaging, labor, and pricing for confectionery.
"""
from dataclasses import dataclass
from typing import Dict, Optional, List

@dataclass
class ConfectioneryPricingCalculator:
    ingredient_costs: Dict[str, float]
    packaging_cost_per_unit: float
    labor_hours: float
    hourly_rate: float = 25.0
    units_produced: int = 50
    overhead_pct: float = 25.0
    profit_margin_pct: float = 50.0

    def total_ingredient_cost(self) -> float:
        return sum(self.ingredient_costs.values())

    def total_packaging_cost(self) -> float:
        return self.packaging_cost_per_unit * self.units_produced

    def labor_cost(self) -> float:
        return self.labor_hours * self.hourly_rate

    def total_cost(self) -> float:
        return self.total_ingredient_cost() + self.total_packaging_cost() + self.labor_cost()

    def overhead(self) -> float:
        return self.total_cost() * (self.overhead_pct / 100)

    def cost_per_unit(self) -> float:
        if self.units_produced == 0:
            return 0
        return (self.total_cost() + self.overhead()) / self.units_produced

    def wholesale_price(self) -> float:
        return self.cost_per_unit() * (1 + self.profit_margin_pct / 100)

    def retail_price(self, markup: float = 2.0) -> float:
        return self.wholesale_price() * markup

    def stats(self) -> Dict:
        return {
            "total_ingredient_cost": round(self.total_ingredient_cost(), 2),
            "total_packaging_cost": round(self.total_packaging_cost(), 2),
            "labor_cost": round(self.labor_cost(), 2),
            "overhead": round(self.overhead(), 2),
            "cost_per_unit": round(self.cost_per_unit(), 2),
            "wholesale_price": round(self.wholesale_price(), 2),
            "retail_price": round(self.retail_price(), 2),
        }

def run():
    cpc = ConfectioneryPricingCalculator(
        ingredient_costs={"chocolate": 20, "cream": 8, "nuts": 12, "sugar": 3},
        packaging_cost_per_unit=0.5, labor_hours=5, hourly_rate=30, units_produced=100,
    )
    print(cpc.stats())

if __name__ == "__main__":
    run()
