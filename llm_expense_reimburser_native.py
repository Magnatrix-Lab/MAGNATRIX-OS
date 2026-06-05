"""Native stdlib module: Expense Reimburser
Validates and calculates reimbursement totals from expense reports.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum
from datetime import datetime

class ExpenseCategory(Enum):
    TRAVEL = "travel"
    MEALS = "meals"
    LODGING = "lodging"
    SUPPLIES = "supplies"
    ENTERTAINMENT = "entertainment"

@dataclass
class ExpenseItem:
    date: str
    category: ExpenseCategory
    amount: float
    receipt: bool = False
    policy_limit: float = 0.0

@dataclass
class ExpenseReimburser:
    employee_name: str
    report_date: str
    expenses: List[ExpenseItem] = field(default_factory=list)

    def total_amount(self) -> float:
        return sum(e.amount for e in self.expenses)

    def valid_total(self) -> float:
        valid = 0.0
        for e in self.expenses:
            if not e.receipt:
                continue
            if e.policy_limit > 0 and e.amount > e.policy_limit:
                valid += e.policy_limit
            else:
                valid += e.amount
        return valid

    def by_category(self) -> Dict[str, float]:
        totals = {}
        for e in self.expenses:
            cat = e.category.value
            totals[cat] = totals.get(cat, 0) + e.amount
        return totals

    def stats(self) -> Dict:
        return {
            "employee": self.employee_name,
            "total_claimed": round(self.total_amount(), 2),
            "valid_total": round(self.valid_total(), 2),
            "by_category": self.by_category(),
            "item_count": len(self.expenses),
        }

def run():
    er = ExpenseReimburser(
        employee_name="Tom Baker",
        report_date="2024-06-01",
        expenses=[
            ExpenseItem("2024-05-28", ExpenseCategory.TRAVEL, 450.00, receipt=True, policy_limit=500),
            ExpenseItem("2024-05-28", ExpenseCategory.LODGING, 180.00, receipt=True, policy_limit=200),
            ExpenseItem("2024-05-29", ExpenseCategory.MEALS, 85.00, receipt=True, policy_limit=75),
            ExpenseItem("2024-05-29", ExpenseCategory.SUPPLIES, 42.00, receipt=False),
        ]
    )
    print(er.stats())

if __name__ == "__main__":
    run()
