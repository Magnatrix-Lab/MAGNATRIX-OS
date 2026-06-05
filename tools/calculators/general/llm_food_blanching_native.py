"""Food Blanching Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FoodBlanching:
    product_weight_kg: float
    water_temp_c: float = 100.0
    blanching_time_seconds: float = 120.0
    product_type: str = "vegetable"
    initial_temp_c: float = 20.0

    def heat_required_kj(self) -> float:
        specific_heat = 3.8
        return round(self.product_weight_kg * specific_heat * (self.water_temp_c - self.initial_temp_c), 2)

    def steam_required_kg(self) -> float:
        latent_heat = 2260
        if latent_heat <= 0:
            return 0.0
        return round(self.heat_required_kj() / latent_heat, 3)

    def water_required_liters(self) -> float:
        return round(self.product_weight_kg * 5, 1)

    def peroxidase_inactivation_percent(self) -> float:
        inactivation_rates = {"vegetable": 0.5, "fruit": 0.3, "leafy": 0.7}
        rate = inactivation_rates.get(self.product_type, 0.5)
        return round(min(100, rate * self.blanching_time_seconds), 2)

    def quality_retention_percent(self) -> float:
        inactivation = self.peroxidase_inactivation_percent()
        overcook = max(0, (self.blanching_time_seconds - 120) / 60.0 * 5)
        return round(max(50, 95 - overcook), 2)

    def nutrient_loss_percent(self) -> float:
        time_factor = self.blanching_time_seconds / 60.0
        return round(min(50, time_factor * 3), 2)

    def cooling_time_seconds(self, cooling_water_temp_c: float = 15.0) -> float:
        delta = self.water_temp_c - cooling_water_temp_c
        return round(delta / 2.0, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "heat_required_kj": self.heat_required_kj(),
            "peroxidase_inactivation_percent": self.peroxidase_inactivation_percent(),
            "quality_retention_percent": self.quality_retention_percent(),
        }

    def run(self):
        print("=" * 60)
        print("FOOD BLANCHING CALCULATOR")
        print("=" * 60)
        blanch = FoodBlanching(
            product_weight_kg=50, water_temp_c=100,
            blanching_time_seconds=90, product_type="vegetable"
        )
        print(f"Product: {blanch.product_weight_kg} kg {blanch.product_type}")
        print(f"Water temp: {blanch.water_temp_c} C")
        print(f"Blanch time: {blanch.blanching_time_seconds} s")
        print(f"Heat required: {blanch.heat_required_kj():.2f} kJ")
        print(f"Steam required: {blanch.steam_required_kg():.3f} kg")
        print(f"Peroxidase inactivation: {blanch.peroxidase_inactivation_percent():.2f}%")
        print(f"Quality retention: {blanch.quality_retention_percent():.2f}%")
        print(f"Nutrient loss: {blanch.nutrient_loss_percent():.2f}%")
        print(f"Cooling time: {blanch.cooling_time_seconds():.1f} s")
        print(f"Stats: {blanch.stats()}")

if __name__ == "__main__":
    FoodBlanching(0).run()
