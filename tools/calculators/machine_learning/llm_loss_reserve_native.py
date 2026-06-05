"""Native stdlib module: Loss Reserve Calculator
Calculates IBNR reserves and loss development factors for insurance.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class AccidentYear:
    year: int
    reported_claims: float
    paid_claims: float
    case_reserves: float

@dataclass
class LossReserveCalculator:
    line_of_business: str
    accident_years: List[AccidentYear] = field(default_factory=list)
    ibnr_factor: float = 0.15
    tail_factor: float = 1.05

    def total_reported(self) -> float:
        return sum(a.reported_claims for a in self.accident_years)

    def total_paid(self) -> float:
        return sum(a.paid_claims for a in self.accident_years)

    def total_case_reserves(self) -> float:
        return sum(a.case_reserves for a in self.accident_years)

    def ibnr_reserve(self) -> float:
        return self.total_reported() * self.ibnr_factor

    def ultimate_loss(self) -> float:
        return (self.total_reported() + self.ibnr_reserve()) * self.tail_factor

    def reserve_adequacy(self) -> float:
        total_reserve = self.total_case_reserves() + self.ibnr_reserve()
        if total_reserve == 0:
            return 0.0
        return (self.total_reported() / total_reserve) * 100

    def stats(self) -> Dict:
        return {
            "line": self.line_of_business,
            "total_reported": round(self.total_reported(), 2),
            "total_paid": round(self.total_paid(), 2),
            "case_reserves": round(self.total_case_reserves(), 2),
            "ibnr": round(self.ibnr_reserve(), 2),
            "ultimate_loss": round(self.ultimate_loss(), 2),
        }

def run():
    lrc = LossReserveCalculator(
        line_of_business="Auto Liability",
        accident_years=[
            AccidentYear(2022, 2500000, 1800000, 700000),
            AccidentYear(2023, 2200000, 1200000, 1000000),
            AccidentYear(2024, 1500000, 400000, 1100000),
        ],
        ibnr_factor=0.12,
        tail_factor=1.03
    )
    print(lrc.stats())

if __name__ == "__main__":
    run()
