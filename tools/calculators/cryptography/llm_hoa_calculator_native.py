"""Native stdlib module: HOA Calculator
Calculates HOA fees, reserve fund contributions, and special assessments.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class BudgetItem:
    name: str
    annual_cost: float
    reserve_allocation_pct: float = 0.0

@dataclass
class HOACalculator:
    community_name: str
    total_units: int
    budget_items: List[BudgetItem] = field(default_factory=list)
    management_fee_pct: float = 5.0

    def total_annual_budget(self) -> float:
        return sum(i.annual_cost for i in self.budget_items)

    def reserve_contribution(self) -> float:
        return sum(i.annual_cost * (i.reserve_allocation_pct / 100) for i in self.budget_items)

    def management_fee(self) -> float:
        return self.total_annual_budget() * (self.management_fee_pct / 100)

    def monthly_fee_per_unit(self) -> float:
        if self.total_units == 0:
            return 0.0
        total = self.total_annual_budget() + self.management_fee()
        return total / self.total_units / 12

    def stats(self) -> Dict[str, float]:
        return {
            "community": self.community_name,
            "total_annual_budget": round(self.total_annual_budget(), 2),
            "reserve_contribution": round(self.reserve_contribution(), 2),
            "management_fee": round(self.management_fee(), 2),
            "monthly_fee_per_unit": round(self.monthly_fee_per_unit(), 2),
        }

def run():
    hoa = HOACalculator(
        community_name="Willow Creek",
        total_units=120,
        budget_items=[
            BudgetItem("landscaping", 36000, 10),
            BudgetItem("pool maintenance", 24000, 15),
            BudgetItem("insurance", 18000, 0),
            BudgetItem("utilities", 12000, 0),
            BudgetItem("repairs", 30000, 20),
        ]
    )
    print(hoa.stats())

if __name__ == "__main__":
    run()
