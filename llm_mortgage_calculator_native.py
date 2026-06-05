"""Native stdlib module: Mortgage Calculator
Calculates monthly payments, amortization, and total interest for mortgages.
"""
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class MortgageCalculator:
    principal: float
    annual_rate_pct: float
    years: int
    extra_payment: float = 0.0

    def monthly_rate(self) -> float:
        return (self.annual_rate_pct / 100) / 12

    def num_payments(self) -> int:
        return self.years * 12

    def monthly_payment(self) -> float:
        r = self.monthly_rate()
        n = self.num_payments()
        if r == 0:
            return self.principal / n
        return self.principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

    def total_interest(self) -> float:
        return (self.monthly_payment() + self.extra_payment) * self.num_payments() - self.principal

    def payoff_months(self) -> int:
        if self.extra_payment <= 0:
            return self.num_payments()
        balance = self.principal
        r = self.monthly_rate()
        payment = self.monthly_payment() + self.extra_payment
        months = 0
        while balance > 0 and months < 1200:
            balance = balance * (1 + r) - payment
            months += 1
        return months

    def stats(self) -> Dict:
        return {
            "monthly_payment": round(self.monthly_payment(), 2),
            "total_interest": round(self.total_interest(), 2),
            "total_cost": round(self.principal + self.total_interest(), 2),
            "payoff_months": self.payoff_months(),
        }

def run():
    mc = MortgageCalculator(principal=400000, annual_rate_pct=6.5, years=30, extra_payment=200)
    print(mc.stats())

if __name__ == "__main__":
    run()
