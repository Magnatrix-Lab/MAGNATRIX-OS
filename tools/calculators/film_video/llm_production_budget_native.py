"""Native stdlib module: Production Budget Calculator
Calculates film production budgets by department, crew, and equipment.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class Department(Enum):
    CAMERA = "camera"
    SOUND = "sound"
    LIGHTING = "lighting"
    ART = "art"
    WARDROBE = "wardrobe"
    MAKEUP = "makeup"
    TRANSPORT = "transport"
    CATERING = "catering"
    POST = "post"

@dataclass
class BudgetLine:
    department: Department
    item: str
    cost: float
    quantity: int = 1

@dataclass
class ProductionBudgetCalculator:
    production_name: str
    shoot_days: int
    budget_lines: List[BudgetLine] = field(default_factory=list)
    contingency_pct: float = 10.0

    def total_cost(self) -> float:
        return sum(l.cost * l.quantity for l in self.budget_lines)

    def contingency(self) -> float:
        return self.total_cost() * (self.contingency_pct / 100)

    def grand_total(self) -> float:
        return self.total_cost() + self.contingency()

    def cost_per_day(self) -> float:
        if self.shoot_days == 0:
            return 0.0
        return self.grand_total() / self.shoot_days

    def by_department(self) -> Dict[str, float]:
        totals = {}
        for l in self.budget_lines:
            totals[l.department.value] = totals.get(l.department.value, 0) + (l.cost * l.quantity)
        return totals

    def stats(self) -> Dict:
        return {
            "production": self.production_name,
            "shoot_days": self.shoot_days,
            "total_cost": round(self.total_cost(), 2),
            "contingency": round(self.contingency(), 2),
            "grand_total": round(self.grand_total(), 2),
            "cost_per_day": round(self.cost_per_day(), 2),
            "by_department": {k: round(v, 2) for k, v in self.by_department().items()},
        }

def run():
    pbc = ProductionBudgetCalculator(
        production_name="Short Film",
        shoot_days=5,
        budget_lines=[
            BudgetLine(Department.CAMERA, "Camera rental", 500, 5),
            BudgetLine(Department.LIGHTING, "Light kit", 300, 5),
            BudgetLine(Department.SOUND, "Sound mixer", 200, 5),
            BudgetLine(Department.CATERING, "Catering", 150, 5),
            BudgetLine(Department.TRANSPORT, "Van rental", 100, 5),
            BudgetLine(Department.POST, "Editor", 400, 3),
        ],
        contingency_pct=10
    )
    print(pbc.stats())

if __name__ == "__main__":
    run()
