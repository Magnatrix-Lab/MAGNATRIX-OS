"""Native stdlib module: Jewelry Pricing Calculator
Calculates metal, stone, and labor costs for jewelry pricing.
"""
from dataclasses import dataclass
from typing import Dict, Optional, List

@dataclass
class StoneCost:
    name: str
    carat: float
    price_per_carat: float

@dataclass
class JewelryPricingCalculator:
    metal_type: str
    metal_weight_g: float
    metal_price_per_g: float
    stones: List[StoneCost]
    hours_worked: float
    hourly_rate: float = 50.0
    overhead_pct: float = 30.0
    profit_margin_pct: float = 50.0

    def metal_cost(self) -> float:
        return self.metal_weight_g * self.metal_price_per_g

    def stones_cost(self) -> float:
        return sum(s.carat * s.price_per_carat for s in self.stones)

    def labor_cost(self) -> float:
        return self.hours_worked * self.hourly_rate

    def materials_total(self) -> float:
        return self.metal_cost() + self.stones_cost()

    def overhead(self) -> float:
        return (self.materials_total() + self.labor_cost()) * (self.overhead_pct / 100)

    def total_cost(self) -> float:
        return self.materials_total() + self.labor_cost() + self.overhead()

    def wholesale_price(self) -> float:
        return self.total_cost() * (1 + self.profit_margin_pct / 100)

    def retail_price(self, markup: float = 2.0) -> float:
        return self.wholesale_price() * markup

    def stats(self) -> Dict:
        return {
            "metal_cost": round(self.metal_cost(), 2),
            "stones_cost": round(self.stones_cost(), 2),
            "labor_cost": round(self.labor_cost(), 2),
            "overhead": round(self.overhead(), 2),
            "total_cost": round(self.total_cost(), 2),
            "wholesale_price": round(self.wholesale_price(), 2),
            "retail_price": round(self.retail_price(), 2),
            "stone_details": [{"name": s.name, "cost": round(s.carat * s.price_per_carat, 2)} for s in self.stones],
        }

def run():
    stones = [StoneCost("diamond", 0.5, 3000), StoneCost("sapphire", 1.0, 500)]
    jpc = JewelryPricingCalculator(
        metal_type="gold", metal_weight_g=8, metal_price_per_g=55,
        stones=stones, hours_worked=6, hourly_rate=60,
    )
    print(jpc.stats())

if __name__ == "__main__":
    run()
