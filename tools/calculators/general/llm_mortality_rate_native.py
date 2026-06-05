"""Mortality Rate Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class MortalityRate:
    initial_count: int
    deaths: int
    period_days: int = 365
    animal_type: str = "cattle"

    def mortality_rate_percent(self) -> float:
        if self.initial_count <= 0:
            return 0.0
        return round(self.deaths / self.initial_count * 100, 2)

    def survival_rate_percent(self) -> float:
        return round(100 - self.mortality_rate_percent(), 2)

    def mortality_rate_per_day(self) -> float:
        if self.period_days <= 0:
            return 0.0
        return round(self.mortality_rate_percent() / self.period_days, 4)

    def annualized_mortality(self) -> float:
        if self.period_days <= 0:
            return 0.0
        return round(self.mortality_rate_percent() * 365 / self.period_days, 2)

    def expected_losses(self, total_herd: int) -> int:
        rate = self.mortality_rate_percent() / 100.0
        return int(total_herd * rate)

    def industry_benchmark(self) -> float:
        benchmarks = {"cattle": 2.0, "pig": 5.0, "sheep": 3.0, "chicken": 8.0, "fish": 10.0}
        return benchmarks.get(self.animal_type, 5.0)

    def is_above_benchmark(self) -> bool:
        return self.mortality_rate_percent() > self.industry_benchmark()

    def stats(self) -> Dict[str, float]:
        return {
            "mortality_rate_percent": self.mortality_rate_percent(),
            "survival_rate_percent": self.survival_rate_percent(),
            "annualized_mortality": self.annualized_mortality(),
        }

    def run(self):
        print("=" * 60)
        print("MORTALITY RATE CALCULATOR")
        print("=" * 60)
        mr = MortalityRate(
            initial_count=500, deaths=15, period_days=365, animal_type="cattle"
        )
        print(f"Initial: {mr.initial_count}, Deaths: {mr.deaths}")
        print(f"Mortality: {mr.mortality_rate_percent():.2f}%")
        print(f"Survival: {mr.survival_rate_percent():.2f}%")
        print(f"Per day: {mr.mortality_rate_per_day():.4f}%")
        print(f"Annualized: {mr.annualized_mortality():.2f}%")
        print(f"Benchmark: {mr.industry_benchmark():.2f}%")
        print(f"Above benchmark: {mr.is_above_benchmark()}")
        print(f"Expected losses (1000): {mr.expected_losses(1000)}")
        print(f"Stats: {mr.stats()}")

if __name__ == "__main__":
    MortalityRate(0, 0).run()
