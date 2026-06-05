"""Native stdlib module: Construction Cost Estimator
Estimates construction costs by material, labor, and overhead categories.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class ConstructionType(Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    INFRASTRUCTURE = "infrastructure"

@dataclass
class CostLine:
    category: str
    description: str
    quantity: float
    unit_cost: float
    overhead_pct: float = 10.0

    def total_cost(self) -> float:
        subtotal = self.quantity * self.unit_cost
        return subtotal * (1 + self.overhead_pct / 100)

@dataclass
class ConstructionCostEstimator:
    project_name: str
    construction_type: ConstructionType
    lines: List[CostLine] = field(default_factory=list)
    contingency_pct: float = 5.0

    def subtotal(self) -> float:
        return sum(l.total_cost() for l in self.lines)

    def contingency(self) -> float:
        return self.subtotal() * (self.contingency_pct / 100)

    def total_cost(self) -> float:
        return self.subtotal() + self.contingency()

    def by_category(self) -> Dict[str, float]:
        totals = {}
        for l in self.lines:
            totals[l.category] = totals.get(l.category, 0) + l.total_cost()
        return totals

    def stats(self) -> Dict:
        return {
            "project": self.project_name,
            "type": self.construction_type.value,
            "subtotal": round(self.subtotal(), 2),
            "contingency": round(self.contingency(), 2),
            "total_cost": round(self.total_cost(), 2),
            "by_category": {k: round(v, 2) for k, v in self.by_category().items()},
        }

def run():
    cce = ConstructionCostEstimator(
        project_name="Office Build-Out",
        construction_type=ConstructionType.COMMERCIAL,
        lines=[
            CostLine("materials", " drywall", 2000, 12.50),
            CostLine("materials", " flooring", 1500, 18.00),
            CostLine("labor", " framing crew", 120, 55.00, 15),
            CostLine("labor", " electrical", 80, 65.00, 15),
            CostLine("overhead", " permits", 1, 5000, 0),
        ],
        contingency_pct=8
    )
    print(cce.stats())

if __name__ == "__main__":
    run()
