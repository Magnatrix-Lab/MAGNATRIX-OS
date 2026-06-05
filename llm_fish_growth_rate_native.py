"""Fish Growth Rate Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FishGrowthRate:
    fish_type: str
    initial_weight_g: float
    current_weight_g: float
    days: int
    water_temp_c: float = 25.0

    def weight_gain_g(self) -> float:
        return round(self.current_weight_g - self.initial_weight_g, 2)

    def daily_growth_rate_g(self) -> float:
        if self.days <= 0:
            return 0.0
        return round(self.weight_gain_g() / self.days, 3)

    def specific_growth_rate_percent(self) -> float:
        if self.initial_weight_g <= 0 or self.days <= 0:
            return 0.0
        return round((math.log(self.current_weight_g) - math.log(self.initial_weight_g)) / self.days * 100, 3)

    def growth_rate_per_degree(self) -> float:
        if self.water_temp_c <= 0:
            return 0.0
        return round(self.daily_growth_rate_g() / self.water_temp_c, 4)

    def days_to_target_weight(self, target_weight_g: float) -> float:
        if self.daily_growth_rate_g() <= 0:
            return 0.0
        return round((target_weight_g - self.current_weight_g) / self.daily_growth_rate_g(), 1)

    def condition_factor(self, length_cm: float) -> float:
        if length_cm <= 0:
            return 0.0
        return round(self.current_weight_g * 100 / (length_cm ** 3), 2)

    def temperature_optimal(self) -> float:
        optimal = {"tilapia": 28, "catfish": 27, "carp": 25, "trout": 15, "shrimp": 28, "salmon": 12}
        return optimal.get(self.fish_type, 25)

    def temp_stress_factor(self) -> float:
        optimal = self.temperature_optimal()
        return max(0.5, 1 - abs(self.water_temp_c - optimal) / 10.0)

    def stats(self) -> Dict[str, float]:
        return {
            "weight_gain_g": self.weight_gain_g(),
            "daily_growth_rate_g": self.daily_growth_rate_g(),
            "specific_growth_rate": self.specific_growth_rate_percent(),
        }

    def run(self):
        print("=" * 60)
        print("FISH GROWTH RATE CALCULATOR")
        print("=" * 60)
        fgr = FishGrowthRate(
            fish_type="tilapia", initial_weight_g=50, current_weight_g=200,
            days=90, water_temp_c=26
        )
        print(f"Fish: {fgr.fish_type}")
        print(f"Weight: {fgr.initial_weight_g} -> {fgr.current_weight_g} g")
        print(f"Gain: {fgr.weight_gain_g():.2f} g")
        print(f"Daily growth: {fgr.daily_growth_rate_g():.3f} g/day")
        print(f"SGR: {fgr.specific_growth_rate_percent():.3f}%")
        print(f"Days to 500g: {fgr.days_to_target_weight(500):.1f}")
        print(f"Condition factor (25cm): {fgr.condition_factor(25):.2f}")
        print(f"Temp stress: {fgr.temp_stress_factor():.2f}")
        print(f"Stats: {fgr.stats()}")

if __name__ == "__main__":
    FishGrowthRate("tilapia", 0, 0, 0).run()
