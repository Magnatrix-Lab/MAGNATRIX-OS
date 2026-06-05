"""Native stdlib module: Pottery Pricing Calculator
Calculates material costs, time, and pricing for pottery pieces.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PotteryPricingCalculator:
    clay_cost_per_kg: float
    clay_used_kg: float
    glaze_cost_per_kg: float
    glaze_used_kg: float
    hours_worked: float
    hourly_rate: float = 25.0
    firing_cost_per_piece: float = 5.0
    overhead_pct: float = 30.0
    profit_margin_pct: float = 50.0

    def material_cost(self) -> float:
        return (self.clay_cost_per_kg * self.clay_used_kg +
                self.glaze_cost_per_kg * self.glaze_used_kg +
                self.firing_cost_per_piece)

    def labor_cost(self) -> float:
        return self.hours_worked * self.hourly_rate

    def overhead_cost(self) -> float:
        return (self.material_cost() + self.labor_cost()) * (self.overhead_pct / 100)

    def total_cost(self) -> float:
        return self.material_cost() + self.labor_cost() + self.overhead_cost()

    def wholesale_price(self) -> float:
        return self.total_cost() * (1 + self.profit_margin_pct / 100)

    def retail_price(self, markup: float = 2.0) -> float:
        return self.wholesale_price() * markup

    def stats(self) -> Dict:
        return {
            "material_cost": round(self.material_cost(), 2),
            "labor_cost": round(self.labor_cost(), 2),
            "overhead_cost": round(self.overhead_cost(), 2),
            "total_cost": round(self.total_cost(), 2),
            "wholesale_price": round(self.wholesale_price(), 2),
            "retail_price": round(self.retail_price(), 2),
        }

def run():
    ppc = PotteryPricingCalculator(
        clay_cost_per_kg=2.5, clay_used_kg=1.2,
        glaze_cost_per_kg=8.0, glaze_used_kg=0.15,
        hours_worked=3, hourly_rate=30, firing_cost_per_piece=6,
    )
    print(ppc.stats())

if __name__ == "__main__":
    run()
