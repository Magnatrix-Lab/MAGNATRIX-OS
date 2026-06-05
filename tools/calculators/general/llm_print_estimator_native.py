"""Print Estimator -- quantity, paper, ink, binding, cost, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class PrintEstimator:
    quantity: int = 1000
    pages: int = 32
    color_pages: int = 4
    paper_weight_gsm: float = 80.0
    binding: str = "saddle_stitch"

    def paper_sheets(self) -> int:
        sheets_per_book = math.ceil(self.pages / 2)
        return sheets_per_book * self.quantity

    def paper_weight_total(self) -> float:
        return self.paper_sheets() * self.paper_weight_gsm / 1000000 * 0.7

    def ink_estimate(self) -> Dict[str, float]:
        if self.color_pages == 0:
            return {"black": self.pages * self.quantity * 0.01}
        return {
            "black": (self.pages - self.color_pages) * self.quantity * 0.01,
            "cmyk": self.color_pages * self.quantity * 0.04
        }

    def binding_cost(self, base_cost: float = 0.5) -> float:
        multipliers = {"saddle_stitch": 0.5, "perfect_bind": 1.0, "spiral": 1.2, "hardcover": 3.0}
        return self.quantity * base_cost * multipliers.get(self.binding, 1.0)

    def total_cost(self, paper_cost_per_kg: float = 2.0, ink_cost_per_ml: float = 0.05) -> float:
        paper = self.paper_weight_total() * paper_cost_per_kg
        inks = self.ink_estimate()
        ink_total = sum(v * ink_cost_per_ml for v in inks.values())
        return paper + ink_total + self.binding_cost()

    def cost_per_unit(self) -> float:
        return self.total_cost() / self.quantity if self.quantity > 0 else 0.0

    def stats(self) -> Dict:
        return {"paper_sheets": self.paper_sheets(), "paper_weight_tons": round(self.paper_weight_total(), 3), "binding_cost": round(self.binding_cost(), 2), "total_cost": round(self.total_cost(), 2), "per_unit": round(self.cost_per_unit(), 3)}

def run():
    pe = PrintEstimator(quantity=5000, pages=48, color_pages=8, binding="perfect_bind")
    print(pe.stats())

if __name__ == "__main__":
    run()
