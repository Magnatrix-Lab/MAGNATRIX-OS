"""Loan Calculator — EMI, APR, amortization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class LoanCalculator:
    principal: float = 100000.0
    annual_rate: float = 0.08
    term_months: int = 120

    def monthly_rate(self) -> float:
        return self.annual_rate / 12

    def emi(self) -> float:
        r = self.monthly_rate()
        if r == 0:
            return self.principal / self.term_months
        return self.principal * r * (1 + r)**self.term_months / ((1 + r)**self.term_months - 1)

    def total_payment(self) -> float:
        return self.emi() * self.term_months

    def total_interest(self) -> float:
        return self.total_payment() - self.principal

    def apr(self, fees: float = 0.0) -> float:
        total_cost = self.total_interest() + fees
        return total_cost / self.principal / (self.term_months / 12) * 100

    def amortization_schedule(self) -> List[Dict]:
        schedule = []
        balance = self.principal
        r = self.monthly_rate()
        emi = self.emi()
        for i in range(1, self.term_months + 1):
            interest = balance * r
            principal = emi - interest
            balance -= principal
            schedule.append({"month": i, "emi": round(emi, 2), "interest": round(interest, 2), "principal": round(principal, 2), "balance": round(max(0, balance), 2)})
        return schedule

    def stats(self) -> Dict:
        return {"emi": round(self.emi(), 2), "total_interest": round(self.total_interest(), 2), "total_payment": round(self.total_payment(), 2)}

def run():
    lc = LoanCalculator(principal=200000, annual_rate=0.06, term_months=240)
    print(lc.stats())
    print("First payment:", lc.amortization_schedule()[0])
    print("APR:", lc.apr(5000))

if __name__ == "__main__":
    run()
