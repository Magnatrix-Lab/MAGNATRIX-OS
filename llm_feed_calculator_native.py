"""Native stdlib module: Feed Calculator
Calculates daily feed requirements, FCR, and feed costs for aquaculture.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class FeedCalculator:
    species: str
    total_biomass_kg: float
    feed_rate_pct_body_weight: float
    feed_cost_per_kg: float
    fcr_target: float = 1.5

    def daily_feed_kg(self) -> float:
        return self.total_biomass_kg * (self.feed_rate_pct_body_weight / 100)

    def daily_feed_cost(self) -> float:
        return self.daily_feed_kg() * self.feed_cost_per_kg

    def expected_weight_gain_kg(self) -> float:
        if self.fcr_target == 0:
            return 0.0
        return self.daily_feed_kg() / self.fcr_target

    def monthly_feed_cost(self) -> float:
        return self.daily_feed_cost() * 30

    def stats(self) -> Dict:
        return {
            "species": self.species,
            "biomass_kg": self.total_biomass_kg,
            "daily_feed_kg": round(self.daily_feed_kg(), 2),
            "daily_feed_cost": round(self.daily_feed_cost(), 2),
            "expected_gain_kg": round(self.expected_weight_gain_kg(), 2),
            "monthly_feed_cost": round(self.monthly_feed_cost(), 2),
            "fcr_target": self.fcr_target,
        }

def run():
    fc = FeedCalculator(species="Salmon", total_biomass_kg=10000, feed_rate_pct_body_weight=1.2, feed_cost_per_kg=1.8, fcr_target=1.3)
    print(fc.stats())

if __name__ == "__main__":
    run()
