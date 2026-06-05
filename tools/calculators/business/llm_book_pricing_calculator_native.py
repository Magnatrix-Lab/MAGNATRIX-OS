"""Native stdlib module: Book Pricing Calculator
Calculates material costs, labor, and pricing for handbound books.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class BookPricingCalculator:
    paper_cost_per_ream: float
    sheets_needed: int
    cover_material_cost: float
    thread_cost: float
    glue_cost: float
    endpaper_cost: float
    hours_worked: float
    hourly_rate: float = 30.0
    overhead_pct: float = 25.0
    profit_margin_pct: float = 40.0

    def paper_cost(self) -> float:
        return (self.paper_cost_per_ream / 500) * self.sheets_needed

    def materials_total(self) -> float:
        return self.paper_cost() + self.cover_material_cost + self.thread_cost + self.glue_cost + self.endpaper_cost

    def labor_cost(self) -> float:
        return self.hours_worked * self.hourly_rate

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
            "materials_total": round(self.materials_total(), 2),
            "labor_cost": round(self.labor_cost(), 2),
            "overhead": round(self.overhead(), 2),
            "total_cost": round(self.total_cost(), 2),
            "wholesale_price": round(self.wholesale_price(), 2),
            "retail_price": round(self.retail_price(), 2),
        }

def run():
    bpc = BookPricingCalculator(
        paper_cost_per_ream=15, sheets_needed=40,
        cover_material_cost=8, thread_cost=1, glue_cost=0.5,
        endpaper_cost=2, hours_worked=4, hourly_rate=35,
    )
    print(bpc.stats())

if __name__ == "__main__":
    run()
