"""Harvest Size Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class HarvestSize:
    fish_type: str
    target_weight_g: float
    current_weight_g: float
    growth_rate_g_per_day: float
    survival_rate_percent: float = 90.0
    stocking_count: int = 10000

    def days_to_harvest(self) -> float:
        if self.growth_rate_g_per_day <= 0:
            return 0.0
        return round((self.target_weight_g - self.current_weight_g) / self.growth_rate_g_per_day, 1)

    def harvest_biomass_kg(self) -> float:
        survivors = int(self.stocking_count * self.survival_rate_percent / 100.0)
        return round(survivors * self.target_weight_g / 1000.0, 2)

    def total_harvest_weight_tons(self) -> float:
        return round(self.harvest_biomass_kg() / 1000.0, 3)

    def revenue(self, price_per_kg: float = 3.0) -> float:
        return round(self.harvest_biomass_kg() * price_per_kg, 2)

    def feed_input_tons(self, fcr: float = 1.5) -> float:
        return round(self.harvest_biomass_kg() / 1000.0 * fcr, 3)

    def feed_cost(self, feed_price_per_kg: float = 1.0, fcr: float = 1.5) -> float:
        return round(self.feed_input_tons(fcr) * 1000 * feed_price_per_kg, 2)

    def profit(self, price_per_kg: float = 3.0, feed_price_per_kg: float = 1.0, fcr: float = 1.5) -> float:
        return round(self.revenue(price_per_kg) - self.feed_cost(feed_price_per_kg, fcr), 2)

    def stats(self) -> Dict[str, float]:
        return {
            "days_to_harvest": self.days_to_harvest(),
            "harvest_biomass_kg": self.harvest_biomass_kg(),
            "revenue": self.revenue(),
        }

    def run(self):
        print("=" * 60)
        print("HARVEST SIZE CALCULATOR")
        print("=" * 60)
        hs = HarvestSize(
            fish_type="tilapia", target_weight_g=500, current_weight_g=50,
            growth_rate_g_per_day=3.0, survival_rate_percent=85, stocking_count=10000
        )
        print(f"Fish: {hs.fish_type}")
        print(f"Days to harvest: {hs.days_to_harvest():.1f}")
        print(f"Harvest biomass: {hs.harvest_biomass_kg():.2f} kg")
        print(f"Total: {hs.total_harvest_weight_tons():.3f} tons")
        print(f"Revenue: ${hs.revenue():.2f}")
        print(f"Feed input: {hs.feed_input_tons():.3f} tons")
        print(f"Profit: ${hs.profit():.2f}")
        print(f"Stats: {hs.stats()}")

if __name__ == "__main__":
    HarvestSize("tilapia", 0, 0, 0).run()
