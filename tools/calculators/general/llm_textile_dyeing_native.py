"""Textile Dyeing Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class TextileDyeing:
    fabric_weight_kg: float
    dye_percent_owf: float = 2.0
    liquor_ratio: float = 10.0
    salt_percent: float = 20.0
    dye_type: str = "reactive"

    def liquor_volume_liters(self) -> float:
        return round(self.fabric_weight_kg * self.liquor_ratio, 1)

    def dye_required_kg(self) -> float:
        return round(self.fabric_weight_kg * self.dye_percent_owf / 100.0, 3)

    def salt_required_kg(self) -> float:
        return round(self.liquor_volume_liters() * self.salt_percent / 100.0, 2)

    def dye_cost(self, dye_price_per_kg: float = 15.0) -> float:
        return round(self.dye_required_kg() * dye_price_per_kg, 2)

    def fixation_percent(self) -> float:
        fixations = {"reactive": 75, "direct": 60, "vat": 85, "sulfur": 70, "disperse": 80}
        return fixations.get(self.dye_type, 70)

    def dye_on_fabric_kg(self) -> float:
        dye = self.dye_required_kg()
        fixation = self.fixation_percent() / 100.0
        return round(dye * fixation, 3)

    def color_depth_percent(self) -> float:
        if self.fabric_weight_kg <= 0:
            return 0.0
        return round(self.dye_on_fabric_kg() / self.fabric_weight_kg * 100, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "liquor_volume_L": self.liquor_volume_liters(),
            "dye_required_kg": self.dye_required_kg(),
            "fixation_percent": self.fixation_percent(),
        }

    def run(self):
        print("=" * 60)
        print("TEXTILE DYEING CALCULATOR")
        print("=" * 60)
        dye = TextileDyeing(
            fabric_weight_kg=100.0, dye_percent_owf=3.0,
            liquor_ratio=12.0, salt_percent=25.0, dye_type="reactive"
        )
        print(f"Fabric: {dye.fabric_weight_kg} kg")
        print(f"Dye type: {dye.dye_type}")
        print(f"Liquor volume: {dye.liquor_volume_liters():.1f} L")
        print(f"Dye required: {dye.dye_required_kg():.3f} kg")
        print(f"Salt required: {dye.salt_required_kg():.2f} kg")
        print(f"Fixation: {dye.fixation_percent()}%")
        print(f"Dye on fabric: {dye.dye_on_fabric_kg():.3f} kg")
        print(f"Color depth: {dye.color_depth_percent():.2f}%")
        print(f"Stats: {dye.stats()}")

if __name__ == "__main__":
    TextileDyeing(0).run()
