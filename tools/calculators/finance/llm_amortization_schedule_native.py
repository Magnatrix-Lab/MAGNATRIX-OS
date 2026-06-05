"""Amortization Schedule — loan, mortgage, extra payments, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class AmortizationSchedule:
    principal: float = 100000.0
    annual_rate: float = 0.06
    years: int = 30
    extra_payment: float = 0.0

    def monthly_rate(self) -> float:
        return self.annual_rate / 12

    def num_payments(self) -> int:
        return self.years * 12

    def monthly_payment(self) -> float:
        r = self.monthly_rate()
        n = self.num_payments()
        if r == 0:
            return self.principal / n
        return self.principal * r * (1 + r)**n / ((1 + r)**n - 1)

    def generate(self) -> List[Dict]:
        schedule = []
        balance = self.principal
        r = self.monthly_rate()
        payment = self.monthly_payment() + self.extra_payment
        month = 0
        while balance > 0 and month < self.num_payments() * 2:
            month += 1
            interest = balance * r
            principal = payment - interest
            if principal > balance:
                principal = balance
                balance = 0
            else:
                balance -= principal
            schedule.append({"month": month, "payment": round(payment, 2), "interest": round(interest, 2), "principal": round(principal, 2), "balance": round(balance, 2)})
        return schedule

    def total_interest(self) -> float:
        schedule = self.generate()
        return sum(p["interest"] for p in schedule)

    def time_saved(self) -> int:
        standard = self.num_payments()
        actual = len(self.generate())
        return standard - actual

    def stats(self) -> Dict:
        return {"monthly": round(self.monthly_payment(), 2), "with_extra": round(self.monthly_payment() + self.extra_payment, 2), "total_interest": round(self.total_interest(), 2), "time_saved_months": self.time_saved()}

def run():
    am = AmortizationSchedule(principal=300000, annual_rate=0.045, years=30, extra_payment=200)
    print(am.stats())
    print("Payments:", len(am.generate()))

if __name__ == "__main__":
    run()
