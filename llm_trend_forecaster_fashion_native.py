"""Fashion Trend Forecaster — seasonality, lifecycle, adoption, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class FashionTrendForecaster:
    trend_name: str = ""
    adoption_rates: List[float] = field(default_factory=list)
    """Percentage over time"""

    def lifecycle_stage(self) -> str:
        if not self.adoption_rates:
            return "unknown"
        if self.adoption_rates[-1] < 2:
            return "introduction"
        elif self.adoption_rates[-1] < 16:
            return "growth"
        elif self.adoption_rates[-1] < 50:
            return "maturity"
        return "decline"

    def peak_prediction(self) -> int:
        if not self.adoption_rates:
            return 0
        return self.adoption_rates.index(max(self.adoption_rates))

    def bass_model(self, p: float = 0.03, q: float = 0.38, m: float = 100, periods: int = 20) -> List[float]:
        adopters = [0.0]
        for t in range(1, periods):
            f = p + q * adopters[-1] / m
            new = f * (m - adopters[-1])
            adopters.append(adopters[-1] + new)
        return adopters

    def seasonality_index(self, monthly: List[float]) -> List[float]:
        avg = sum(monthly) / len(monthly) if monthly else 1
        return [m / avg if avg > 0 else 1 for m in monthly]

    def stats(self) -> Dict:
        return {"stage": self.lifecycle_stage(), "peak": self.peak_prediction(), "current": self.adoption_rates[-1] if self.adoption_rates else 0}

def run():
    ftf = FashionTrendForecaster("Skinny Jeans", [1, 3, 8, 15, 30, 45, 50, 48, 40, 30])
    print(ftf.stats())
    print("Bass:", ftf.bass_model()[:5])

if __name__ == "__main__":
    run()
