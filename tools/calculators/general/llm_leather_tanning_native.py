"""Leather Tanning Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class LeatherTanning:
    raw_hide_weight_kg: float
    tanning_method: str = "chrome"
    salt_percent: float = 15.0
    tanning_agent_percent: float = 8.0
    water_ratio: float = 3.0

    def water_required_liters(self) -> float:
        return round(self.raw_hide_weight_kg * self.water_ratio, 1)

    def salt_required_kg(self) -> float:
        return round(self.raw_hide_weight_kg * self.salt_percent / 100.0, 2)

    def tanning_agent_kg(self) -> float:
        return round(self.raw_hide_weight_kg * self.tanning_agent_percent / 100.0, 2)

    def leather_yield_kg(self) -> float:
        yields = {"chrome": 0.65, "vegetable": 0.55, "alum": 0.60, "synthetic": 0.62}
        factor = yields.get(self.tanning_method, 0.60)
        return round(self.raw_hide_weight_kg * factor, 2)

    def effluent_liters(self) -> float:
        water = self.water_required_liters()
        return round(water * 0.85, 1)

    def cost_estimate(self, hide_price_per_kg: float = 2.0,
                      salt_price: float = 0.5,
                      agent_price: float = 5.0) -> float:
        salt_cost = self.salt_required_kg() * salt_price
        agent_cost = self.tanning_agent_kg() * agent_price
        hide_cost = self.raw_hide_weight_kg * hide_price_per_kg
        return round(hide_cost + salt_cost + agent_cost, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "leather_yield_kg": self.leather_yield_kg(),
            "water_required_L": self.water_required_liters(),
            "effluent_L": self.effluent_liters(),
        }

    def run(self):
        print("=" * 60)
        print("LEATHER TANNING CALCULATOR")
        print("=" * 60)
        tan = LeatherTanning(
            raw_hide_weight_kg=500.0, tanning_method="chrome",
            salt_percent=18.0, tanning_agent_percent=10.0
        )
        print(f"Raw hide: {tan.raw_hide_weight_kg} kg")
        print(f"Method: {tan.tanning_method}")
        print(f"Water required: {tan.water_required_liters():.1f} L")
        print(f"Salt required: {tan.salt_required_kg():.2f} kg")
        print(f"Tanning agent: {tan.tanning_agent_kg():.2f} kg")
        print(f"Leather yield: {tan.leather_yield_kg():.2f} kg")
        print(f"Effluent: {tan.effluent_liters():.1f} L")
        print(f"Cost estimate: ${tan.cost_estimate():.2f}")
        print(f"Stats: {tan.stats()}")

if __name__ == "__main__":
    LeatherTanning(0).run()
