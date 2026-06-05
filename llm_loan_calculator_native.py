"""Loan Calculator — circulation, overdue, renewals, holds, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta

@dataclass
class LoanRecord:
    item_id: str
    patron_id: str
    checkout_date: str
    due_date: str
    renewals: int = 0

class LoanCalculator:
    def __init__(self):
        self.loans: List[LoanRecord] = []

    def add_loan(self, l: LoanRecord):
        self.loans.append(l)

    def overdue(self, current_date: str) -> List[LoanRecord]:
        return [l for l in self.loans if l.due_date < current_date]

    def fine(self, loan: LoanRecord, current_date: str, rate_per_day: float = 1.0) -> float:
        if loan.due_date >= current_date:
            return 0.0
        due = datetime.strptime(loan.due_date, "%Y-%m-%d")
        curr = datetime.strptime(current_date, "%Y-%m-%d")
        days = (curr - due).days
        return days * rate_per_day

    def renewal_eligible(self, loan: LoanRecord, max_renewals: int = 2) -> bool:
        return loan.renewals < max_renewals

    def hold_position(self, item_id: str, patron_id: str, holds: List[Dict]) -> int:
        item_holds = [h for h in holds if h["item_id"] == item_id]
        item_holds.sort(key=lambda h: h["date"])
        for i, h in enumerate(item_holds):
            if h["patron_id"] == patron_id:
                return i + 1
        return -1

    def stats(self, current_date: str) -> Dict:
        return {"total_loans": len(self.loans), "overdue": len(self.overdue(current_date))}

def run():
    lc = LoanCalculator()
    lc.add_loan(LoanRecord("B1", "P1", "2024-01-01", "2024-01-15", 0))
    lc.add_loan(LoanRecord("B2", "P2", "2024-01-01", "2024-01-10", 2))
    print(lc.stats("2024-01-20"))
    print("Fine B2:", lc.fine(lc.loans[1], "2024-01-20", 2.0))

if __name__ == "__main__":
    run()
