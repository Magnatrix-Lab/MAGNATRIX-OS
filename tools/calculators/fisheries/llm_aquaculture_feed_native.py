"""Aquaculture Feed Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class AquacultureFeed:
    fish_count: int
    avg_fish_weight_g: float
    feed_rate_percent_body_weight: float = 2.0
    protein_percent: float = 32.0
    feeding_frequency: int = 3

    def total_biomass_kg(self) -> float:
        return round(self.fish_count * self.avg_fish_weight_g / 1000.0, 2)

    def daily_feed_kg(self) -> float:
        return round(self.total_biomass_kg() * self.feed_rate_percent_body_weight / 100.0, 2)

    def feed_per_meal_kg(self) -> float:
        if self.feeding_frequency <= 0:
            return 0.0
        return round(self.daily_feed_kg() / self.feeding_frequency, 3)

    def protein_required_kg(self) -> float:
        return round(self.daily_feed_kg() * self.protein_percent / 100.0, 3)

    def fcr_target(self) -> float:
        fcr_targets = {"tilapia": 1.5, "catfish": 1.8, "carp": 2.0, "trout": 1.2, "shrimp": 1.6, "salmon": 1.1}
        return fcr_targets.get(self.fish_type if hasattr(self, 'fish_type') else "tilapia", 1.5)

    def feed_cost_daily(self, price_per_kg: float = 1.0) -> float:
        return round(self.daily_feed_kg() * price_per_kg, 2)

    def feed_cost_per_kg_fish(self, price_per_kg: float = 1.0,
                               daily_growth_rate_percent: float = 1.0) -> float:
        daily_growth = self.total_biomass_kg() * daily_growth_rate_percent / 100.0
        if daily_growth <= 0:
            return 0.0
        return round(self.feed_cost_daily(price_per_kg) / daily_growth, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "total_biomass_kg": self.total_biomass_kg(),
            "daily_feed_kg": self.daily_feed_kg(),
            "feed_per_meal_kg": self.feed_per_meal_kg(),
        }

    def run(self):
        print("=" * 60)
        print("AQUACULTURE FEED CALCULATOR")
        print("=" * 60)
        af = AquacultureFeed(
            fish_count=5000, avg_fish_weight_g=250,
            feed_rate_percent_body_weight=2.5, protein_percent=35, feeding_frequency=4
        )
        print(f"Fish: {af.fish_count} @ {af.avg_fish_weight_g} g")
        print(f"Biomass: {af.total_biomass_kg():.2f} kg")
        print(f"Daily feed: {af.daily_feed_kg():.2f} kg")
        print(f"Per meal: {af.feed_per_meal_kg():.3f} kg")
        print(f"Protein: {af.protein_required_kg():.3f} kg/day")
        print(f"Feed cost: ${af.feed_cost_daily():.2f}/day")
        print(f"Stats: {af.stats()}")

if __name__ == "__main__":
    AquacultureFeed(0, 0).run()
