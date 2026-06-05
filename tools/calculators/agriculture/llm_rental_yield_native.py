"""Native stdlib module: Rental Yield Calculator
Computes gross and net rental yields, cap rate, and cash-on-cash return.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class RentalYieldCalculator:
    property_price: float
    monthly_rent: float
    annual_expenses: float
    down_payment: float
    loan_amount: float = 0.0
    annual_interest: float = 0.0

    def annual_rent(self) -> float:
        return self.monthly_rent * 12

    def gross_yield_pct(self) -> float:
        if self.property_price == 0:
            return 0.0
        return (self.annual_rent() / self.property_price) * 100

    def net_yield_pct(self) -> float:
        if self.property_price == 0:
            return 0.0
        return ((self.annual_rent() - self.annual_expenses) / self.property_price) * 100

    def cap_rate_pct(self) -> float:
        if self.property_price == 0:
            return 0.0
        noi = self.annual_rent() - self.annual_expenses
        return (noi / self.property_price) * 100

    def cash_on_cash_pct(self) -> float:
        if self.down_payment == 0:
            return 0.0
        cash_flow = self.annual_rent() - self.annual_expenses - self.annual_interest
        return (cash_flow / self.down_payment) * 100

    def stats(self) -> Dict[str, float]:
        return {
            "gross_yield_pct": round(self.gross_yield_pct(), 2),
            "net_yield_pct": round(self.net_yield_pct(), 2),
            "cap_rate_pct": round(self.cap_rate_pct(), 2),
            "cash_on_cash_pct": round(self.cash_on_cash_pct(), 2),
            "annual_rent": round(self.annual_rent(), 2),
        }

def run():
    ry = RentalYieldCalculator(property_price=500000, monthly_rent=3000, annual_expenses=8000, down_payment=100000, loan_amount=400000, annual_interest=24000)
    print(ry.stats())

if __name__ == "__main__":
    run()
