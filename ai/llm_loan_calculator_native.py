"""LLM Loan Calculator — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class LoanType(Enum):
    FIXED = auto()
    VARIABLE = auto()
    INTEREST_ONLY = auto()
    AMORTIZING = auto()

class LoanCalculator:
    def __init__(self) -> None:
        self._schedule: List[Dict[str, Any]] = []

    def calculate_monthly_payment(self, principal: float, annual_rate: float, years: int) -> float:
        if annual_rate == 0:
            return principal / (years * 12)
        monthly_rate = annual_rate / 12
        n_payments = years * 12
        payment = principal * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
        return payment

    def generate_amortization_schedule(self, principal: float, annual_rate: float, years: int) -> List[Dict[str, Any]]:
        monthly_payment = self.calculate_monthly_payment(principal, annual_rate, years)
        balance = principal
        monthly_rate = annual_rate / 12
        schedule = []
        for month in range(1, years * 12 + 1):
            interest = balance * monthly_rate
            principal_paid = monthly_payment - interest
            balance = max(0, balance - principal_paid)
            schedule.append({"month": month, "payment": monthly_payment, "interest": interest, "principal": principal_paid, "balance": balance})
        self._schedule = schedule
        return schedule

    def total_interest(self, principal: float, annual_rate: float, years: int) -> float:
        monthly_payment = self.calculate_monthly_payment(principal, annual_rate, years)
        total_paid = monthly_payment * years * 12
        return total_paid - principal

    def apr_to_apr(self, nominal_rate: float, compounding_periods: int = 12) -> float:
        return (1 + nominal_rate / compounding_periods) ** compounding_periods - 1

    def get_stats(self, principal: float, annual_rate: float, years: int) -> Dict[str, Any]:
        monthly = self.calculate_monthly_payment(principal, annual_rate, years)
        total = monthly * years * 12
        return {"principal": principal, "monthly": monthly, "total": total, "total_interest": total - principal, "years": years}

def run() -> None:
    print("Loan Calculator test")
    e = LoanCalculator()
    monthly = e.calculate_monthly_payment(300000, 0.05, 30)
    print("  Monthly payment: " + str(monthly))
    schedule = e.generate_amortization_schedule(300000, 0.05, 30)
    print("  Schedule length: " + str(len(schedule)))
    print("  First payment: " + str(schedule[0]))
    print("  Total interest: " + str(e.total_interest(300000, 0.05, 30)))
    print("  Stats: " + str(e.get_stats(300000, 0.05, 30)))
    print("Loan Calculator test complete.")

if __name__ == "__main__":
    run()
