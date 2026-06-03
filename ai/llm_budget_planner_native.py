"""LLM Budget Planner — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class BudgetCategory(Enum):
    INCOME = auto()
    EXPENSE = auto()
    SAVINGS = auto()
    INVESTMENT = auto()
    DEBT = auto()

@dataclass
class BudgetItem:
    id: str
    name: str
    category: BudgetCategory
    amount: float
    recurring: bool = False
    frequency: str = "monthly"
    metadata: Dict[str, Any] = field(default_factory=dict)

class BudgetPlanner:
    def __init__(self) -> None:
        self._items: List[BudgetItem] = []

    def add_item(self, item: BudgetItem) -> None:
        self._items.append(item)

    def remove_item(self, item_id: str) -> bool:
        for i, item in enumerate(self._items):
            if item.id == item_id:
                self._items.pop(i)
                return True
        return False

    def get_total_by_category(self, category: BudgetCategory) -> float:
        return sum(item.amount for item in self._items if item.category == category)

    def get_monthly_income(self) -> float:
        return sum(self.get_total_by_category(c) for c in [BudgetCategory.INCOME])

    def get_monthly_expenses(self) -> float:
        return sum(self.get_total_by_category(c) for c in [BudgetCategory.EXPENSE, BudgetCategory.DEBT])

    def get_balance(self) -> float:
        return self.get_monthly_income() - self.get_monthly_expenses()

    def get_savings_rate(self) -> float:
        income = self.get_monthly_income()
        if income == 0:
            return 0.0
        return self.get_total_by_category(BudgetCategory.SAVINGS) / income

    def get_breakdown(self) -> Dict[str, float]:
        return {cat.name: self.get_total_by_category(cat) for cat in BudgetCategory}

    def get_stats(self) -> Dict[str, Any]:
        return {"items": len(self._items), "income": self.get_monthly_income(), "expenses": self.get_monthly_expenses(), "balance": self.get_balance(), "savings_rate": self.get_savings_rate()}

def run() -> None:
    print("Budget Planner test")
    e = BudgetPlanner()
    e.add_item(BudgetItem("i1", "Salary", BudgetCategory.INCOME, 5000.0, True))
    e.add_item(BudgetItem("i2", "Rent", BudgetCategory.EXPENSE, 1500.0, True))
    e.add_item(BudgetItem("i3", "Food", BudgetCategory.EXPENSE, 600.0, True))
    e.add_item(BudgetItem("i4", "Savings", BudgetCategory.SAVINGS, 1000.0, True))
    e.add_item(BudgetItem("i5", "Investment", BudgetCategory.INVESTMENT, 500.0, True))
    e.add_item(BudgetItem("i6", "Loan", BudgetCategory.DEBT, 300.0, True))
    print("  Income: " + str(e.get_monthly_income()))
    print("  Expenses: " + str(e.get_monthly_expenses()))
    print("  Balance: " + str(e.get_balance()))
    print("  Savings rate: " + str(e.get_savings_rate()))
    print("  Breakdown: " + str(e.get_breakdown()))
    print("  Stats: " + str(e.get_stats()))
    print("Budget Planner test complete.")

if __name__ == "__main__":
    run()
