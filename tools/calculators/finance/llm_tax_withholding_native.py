"""Native stdlib module: Tax Withholding Calculator
Estimates tax withholding based on filing status, allowances, and income brackets.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class FilingStatus(Enum):
    SINGLE = "single"
    MARRIED = "married"
    HEAD_OF_HOUSEHOLD = "head_of_household"

@dataclass
class TaxWithholdingCalculator:
    annual_salary: float
    filing_status: FilingStatus
    allowances: int = 0
    additional_withholding: float = 0.0

    def _brackets(self) -> list:
        if self.filing_status == FilingStatus.SINGLE:
            return [(0, 11600, 0.10), (11600, 47150, 0.12), (47150, 100525, 0.22), (100525, 191950, 0.24), (191950, 243725, 0.32), (243725, 609350, 0.35), (609350, float('inf'), 0.37)]
        elif self.filing_status == FilingStatus.MARRIED:
            return [(0, 23200, 0.10), (23200, 94300, 0.12), (94300, 201050, 0.22), (201050, 383900, 0.24), (383900, 487450, 0.32), (487450, 731200, 0.35), (731200, float('inf'), 0.37)]
        else:
            return [(0, 16550, 0.10), (16550, 63100, 0.12), (63100, 100500, 0.22), (100500, 191950, 0.24), (191950, 243700, 0.32), (243700, 609350, 0.35), (609350, float('inf'), 0.37)]

    def estimated_tax(self) -> float:
        tax = 0.0
        taxable = max(0, self.annual_salary - (self.allowances * 4600))
        for low, high, rate in self._brackets():
            if taxable > high:
                tax += (high - low) * rate
            else:
                tax += max(0, taxable - low) * rate
                break
        return tax + self.additional_withholding

    def monthly_withholding(self) -> float:
        return self.estimated_tax() / 12

    def stats(self) -> Dict[str, float]:
        return {
            "estimated_annual_tax": round(self.estimated_tax(), 2),
            "monthly_withholding": round(self.monthly_withholding(), 2),
            "effective_rate_pct": round((self.estimated_tax() / max(1, self.annual_salary)) * 100, 2),
        }

def run():
    tw = TaxWithholdingCalculator(annual_salary=85000, filing_status=FilingStatus.SINGLE, allowances=2, additional_withholding=100)
    print(tw.stats())

if __name__ == "__main__":
    run()
