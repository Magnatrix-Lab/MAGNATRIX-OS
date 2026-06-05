"""Crop Yield Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CropYield:
    crop_type: str
    area_ha: float
    plant_population_per_ha: float
    expected_weight_per_plant_kg: float
    harvest_loss_percent: float = 5.0

    def total_plants(self) -> int:
        return int(self.area_ha * self.plant_population_per_ha)

    def gross_yield_tons(self) -> float:
        return round(self.area_ha * self.plant_population_per_ha * self.expected_weight_per_plant_kg / 1000.0, 2)

    def net_yield_tons(self) -> float:
        gross = self.gross_yield_tons()
        return round(gross * (1 - self.harvest_loss_percent / 100.0), 2)

    def yield_per_ha_tons(self) -> float:
        if self.area_ha <= 0:
            return 0.0
        return round(self.net_yield_tons() / self.area_ha, 2)

    def yield_per_acre_tons(self) -> float:
        return round(self.yield_per_ha_tons() / 2.471, 2)

    def yield_in_bu_per_acre(self) -> float:
        bu_factors = {"corn": 39.37, "wheat": 60.0, "soybean": 60.0, "rice": 45.0, "barley": 48.0}
        factor = bu_factors.get(self.crop_type, 50.0)
        return round(self.yield_per_ha_tons() * 1000 / factor, 2)

    def revenue(self, price_per_ton: float) -> float:
        return round(self.net_yield_tons() * price_per_ton, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "total_plants": self.total_plants(),
            "gross_yield_tons": self.gross_yield_tons(),
            "net_yield_tons": self.net_yield_tons(),
            "yield_per_ha_tons": self.yield_per_ha_tons(),
        }

    def run(self):
        print("=" * 60)
        print("CROP YIELD CALCULATOR")
        print("=" * 60)
        crop = CropYield(
            crop_type="corn", area_ha=10, plant_population_per_ha=75000,
            expected_weight_per_plant_kg=0.25, harvest_loss_percent=8
        )
        print(f"Crop: {crop.crop_type}, Area: {crop.area_ha} ha")
        print(f"Total plants: {crop.total_plants()}")
        print(f"Gross yield: {crop.gross_yield_tons():.2f} tons")
        print(f"Net yield: {crop.net_yield_tons():.2f} tons")
        print(f"Yield/ha: {crop.yield_per_ha_tons():.2f} tons/ha")
        print(f"Yield/acre: {crop.yield_per_acre_tons():.2f} tons/acre")
        print(f"Bushels/acre: {crop.yield_in_bu_per_acre():.2f} bu/acre")
        print(f"Revenue @ $200/ton: ${crop.revenue(200):.2f}")
        print(f"Stats: {crop.stats()}")

if __name__ == "__main__":
    CropYield("wheat", 0, 0, 0).run()
