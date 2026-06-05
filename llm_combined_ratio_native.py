"""Native stdlib module: Combined Ratio Calculator
Calculates insurance combined ratio, loss ratio, and expense ratio.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class CombinedRatioCalculator:
    earned_premium: float
    incurred_losses: float
    loss_adjustment_expenses: float
    underwriting_expenses: float
    dividend_expenses: float = 0.0

    def loss_ratio(self) -> float:
        if self.earned_premium == 0:
            return 0.0
        return ((self.incurred_losses + self.loss_adjustment_expenses) / self.earned_premium) * 100

    def expense_ratio(self) -> float:
        if self.earned_premium == 0:
            return 0.0
        return ((self.underwriting_expenses + self.dividend_expenses) / self.earned_premium) * 100

    def combined_ratio(self) -> float:
        return self.loss_ratio() + self.expense_ratio()

    def underwriting_profit_margin(self) -> float:
        return 100 - self.combined_ratio()

    def profitable(self) -> bool:
        return self.combined_ratio() < 100

    def stats(self) -> Dict:
        return {
            "earned_premium": round(self.earned_premium, 2),
            "loss_ratio_pct": round(self.loss_ratio(), 2),
            "expense_ratio_pct": round(self.expense_ratio(), 2),
            "combined_ratio_pct": round(self.combined_ratio(), 2),
            "profit_margin_pct": round(self.underwriting_profit_margin(), 2),
            "profitable": self.profitable(),
        }

def run():
    crc = CombinedRatioCalculator(earned_premium=10000000, incurred_losses=6500000, loss_adjustment_expenses=500000, underwriting_expenses=2500000)
    print(crc.stats())

if __name__ == "__main__":
    run()
