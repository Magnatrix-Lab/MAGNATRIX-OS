"""Native stdlib module: Garment Costing Calculator
Calculates garment production costs by material, labor, and overhead.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class CostComponent:
    name: str
    cost_per_unit: float
    quantity: float

@dataclass
class GarmentCostingCalculator:
    style_number: str
    target_qty: int
    components: List[CostComponent] = field(default_factory=list)
    overhead_pct: float = 15.0
    profit_margin_pct: float = 25.0

    def material_cost(self) -> float:
        return sum(c.cost_per_unit * c.quantity for c in self.components if "labor" not in c.name.lower())

    def labor_cost(self) -> float:
        return sum(c.cost_per_unit * c.quantity for c in self.components if "labor" in c.name.lower())

    def total_cost(self) -> float:
        return (self.material_cost() + self.labor_cost()) * (1 + self.overhead_pct / 100)

    def cost_per_garment(self) -> float:
        if self.target_qty == 0:
            return 0.0
        return self.total_cost() / self.target_qty

    def wholesale_price(self) -> float:
        return self.cost_per_garment() * (1 + self.profit_margin_pct / 100)

    def stats(self) -> Dict:
        return {
            "style": self.style_number,
            "quantity": self.target_qty,
            "material_cost": round(self.material_cost(), 2),
            "labor_cost": round(self.labor_cost(), 2),
            "total_cost": round(self.total_cost(), 2),
            "cost_per_garment": round(self.cost_per_garment(), 2),
            "wholesale_price": round(self.wholesale_price(), 2),
        }

def run():
    gcc = GarmentCostingCalculator(
        style_number="TS-2024-01",
        target_qty=1000,
        components=[
            CostComponent("fabric", 4.50, 1.2),
            CostComponent("thread", 0.30, 1),
            CostComponent("label", 0.15, 1),
            CostComponent("labor_cut", 0.80, 1),
            CostComponent("labor_sew", 1.50, 1),
            CostComponent("labor_finish", 0.50, 1),
        ],
        overhead_pct=15,
        profit_margin_pct=30
    )
    print(gcc.stats())

if __name__ == "__main__":
    run()
