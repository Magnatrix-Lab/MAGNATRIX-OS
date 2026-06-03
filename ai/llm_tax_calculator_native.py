"""LLM Tax Calculator — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

@dataclass
class TaxBracket:
    min_income: float
    max_income: float
    rate: float

class TaxCalculator:
    def __init__(self) -> None:
        self._brackets: List[TaxBracket] = []
        self._deductions: Dict[str, float] = {}

    def set_brackets(self, brackets: List[TaxBracket]) -> None:
        self._brackets = sorted(brackets, key=lambda b: b.min_income)

    def add_deduction(self, name: str, amount: float) -> None:
        self._deductions[name] = amount

    def calculate_tax(self, income: float) -> Dict[str, Any]:
        total_deductions = sum(self._deductions.values())
        taxable = max(0, income - total_deductions)
        tax_breakdown = []
        total_tax = 0.0
        remaining = taxable
        for bracket in self._brackets:
            if remaining <= 0:
                break
            bracket_range = bracket.max_income - bracket.min_income if bracket.max_income > 0 else remaining
            taxable_in_bracket = min(remaining, bracket_range)
            tax_in_bracket = taxable_in_bracket * bracket.rate
            tax_breakdown.append({"bracket": str(bracket.min_income) + "-" + str(bracket.max_income), "rate": bracket.rate, "taxable": taxable_in_bracket, "tax": tax_in_bracket})
            total_tax += tax_in_bracket
            remaining -= taxable_in_bracket
        effective_rate = total_tax / income if income > 0 else 0.0
        return {"income": income, "deductions": total_deductions, "taxable": taxable, "tax": total_tax, "effective_rate": effective_rate, "breakdown": tax_breakdown, "net_income": income - total_tax}

    def get_stats(self) -> Dict[str, Any]:
        return {"brackets": len(self._brackets), "deductions": len(self._deductions)}

def run() -> None:
    print("Tax Calculator test")
    e = TaxCalculator()
    e.set_brackets([TaxBracket(0, 50000, 0.1), TaxBracket(50000, 100000, 0.2), TaxBracket(100000, 200000, 0.3), TaxBracket(200000, 0, 0.4)])
    e.add_deduction("standard", 12000)
    e.add_deduction("charity", 5000)
    result = e.calculate_tax(150000)
    print("  Tax: " + str(result["tax"]))
    print("  Effective rate: " + str(result["effective_rate"]))
    print("  Net income: " + str(result["net_income"]))
    print("  Stats: " + str(e.get_stats()))
    print("Tax Calculator test complete.")

if __name__ == "__main__":
    run()
