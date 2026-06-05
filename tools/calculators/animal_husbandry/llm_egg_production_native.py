"""Egg Production Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class EggProduction:
    hen_count: int
    eggs_per_hen_per_day: float
    avg_egg_weight_g: float = 58.0
    laying_cycle_days: int = 365
    mortality_percent: float = 5.0

    def daily_egg_count(self) -> int:
        return int(self.hen_count * self.eggs_per_hen_per_day)

    def annual_egg_count(self) -> int:
        return int(self.daily_egg_count() * self.laying_cycle_days)

    def daily_egg_weight_kg(self) -> float:
        return round(self.daily_egg_count() * self.avg_egg_weight_g / 1000.0, 2)

    def annual_egg_weight_tons(self) -> float:
        return round(self.annual_egg_count() * self.avg_egg_weight_g / 1000.0 / 1000.0, 3)

    def dozen_per_day(self) -> float:
        return round(self.daily_egg_count() / 12.0, 1)

    def carton_boxes_per_day(self, eggs_per_carton: int = 30) -> float:
        return round(self.daily_egg_count() / eggs_per_carton, 1)

    def revenue(self, price_per_egg: float = 0.15) -> float:
        return round(self.annual_egg_count() * price_per_egg, 2)

    def feed_conversion_ratio(self, daily_feed_kg: float = 0.12) -> float:
        egg_weight = self.daily_egg_weight_kg()
        if egg_weight <= 0:
            return 0.0
        total_feed = self.hen_count * daily_feed_kg
        return round(total_feed / egg_weight, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "daily_egg_count": self.daily_egg_count(),
            "annual_egg_count": self.annual_egg_count(),
            "annual_egg_weight_tons": self.annual_egg_weight_tons(),
        }

    def run(self):
        print("=" * 60)
        print("EGG PRODUCTION CALCULATOR")
        print("=" * 60)
        ep = EggProduction(
            hen_count=1000, eggs_per_hen_per_day=0.85, avg_egg_weight_g=60
        )
        print(f"Hens: {ep.hen_count}")
        print(f"Daily eggs: {ep.daily_egg_count()}")
        print(f"Annual eggs: {ep.annual_egg_count()}")
        print(f"Daily weight: {ep.daily_egg_weight_kg():.2f} kg")
        print(f"Annual weight: {ep.annual_egg_weight_tons():.3f} tons")
        print(f"Dozen/day: {ep.dozen_per_day():.1f}")
        print(f"Revenue: ${ep.revenue():.2f}")
        print(f"FCR: {ep.feed_conversion_ratio():.2f}")
        print(f"Stats: {ep.stats()}")

if __name__ == "__main__":
    EggProduction(0, 0).run()
