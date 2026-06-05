"""Native stdlib module: Payroll Calculator
Calculates gross pay, deductions, and net pay for employees.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Deduction:
    name: str
    amount: float
    is_pct: bool = False

@dataclass
class PayrollCalculator:
    employee_name: str
    pay_period: str
    gross_pay: float
    deductions: List[Deduction] = field(default_factory=list)
    hourly_rate: float = 0.0
    hours_worked: float = 0.0

    def total_deductions(self) -> float:
        total = 0.0
        for d in self.deductions:
            if d.is_pct:
                total += self.gross_pay * (d.amount / 100)
            else:
                total += d.amount
        return total

    def net_pay(self) -> float:
        return max(0, self.gross_pay - self.total_deductions())

    def effective_tax_rate(self) -> float:
        if self.gross_pay == 0:
            return 0.0
        return (self.total_deductions() / self.gross_pay) * 100

    def stats(self) -> Dict[str, float]:
        return {
            "gross_pay": round(self.gross_pay, 2),
            "total_deductions": round(self.total_deductions(), 2),
            "net_pay": round(self.net_pay(), 2),
            "effective_tax_rate_pct": round(self.effective_tax_rate(), 2),
        }

def run():
    pc = PayrollCalculator(
        employee_name="Sarah Lee",
        pay_period="June 2024",
        gross_pay=5000,
        deductions=[
            Deduction("federal_tax", 22, True),
            Deduction("state_tax", 5, True),
            Deduction("health_insurance", 250, False),
            Deduction("retirement_401k", 300, False),
        ]
    )
    print(pc.stats())

if __name__ == "__main__":
    run()
