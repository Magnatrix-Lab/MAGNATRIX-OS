"""Fish Stocking Density Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FishStockingDensity:
    pond_area_sqm: float
    pond_depth_m: float
    fish_type: str
    fish_weight_g: float

    def pond_volume_m3(self) -> float:
        return round(self.pond_area_sqm * self.pond_depth_m, 1)

    def recommended_density_kg_per_m3(self) -> float:
        densities = {"tilapia": 3.0, "catfish": 2.0, "carp": 2.5, "trout": 10.0, "shrimp": 1.5, "salmon": 15.0}
        return densities.get(self.fish_type, 2.0)

    def max_biomass_kg(self) -> float:
        return round(self.pond_volume_m3() * self.recommended_density_kg_per_m3(), 1)

    def max_fish_count(self) -> int:
        if self.fish_weight_g <= 0:
            return 0
        return int(self.max_biomass_kg() * 1000 / self.fish_weight_g)

    def current_density_percent(self, current_fish_count: int) -> float:
        max_count = self.max_fish_count()
        if max_count <= 0:
            return 0.0
        return round(current_fish_count / max_count * 100, 2)

    def oxygen_demand_kg_per_day(self, current_fish_count: int) -> float:
        return round(current_fish_count * self.fish_weight_g / 1000.0 * 0.02, 2)

    def feed_requirement_kg_per_day(self, current_fish_count: int,
                                     fcr: float = 1.5) -> float:
        biomass = current_fish_count * self.fish_weight_g / 1000.0
        growth_rate = 0.02
        return round(biomass * growth_rate * fcr, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "pond_volume_m3": self.pond_volume_m3(),
            "max_biomass_kg": self.max_biomass_kg(),
            "max_fish_count": self.max_fish_count(),
        }

    def run(self):
        print("=" * 60)
        print("FISH STOCKING DENSITY CALCULATOR")
        print("=" * 60)
        fsd = FishStockingDensity(
            pond_area_sqm=500, pond_depth_m=1.5, fish_type="tilapia", fish_weight_g=200
        )
        print(f"Pond: {fsd.pond_area_sqm} sqm x {fsd.pond_depth_m} m")
        print(f"Volume: {fsd.pond_volume_m3():.1f} m3")
        print(f"Fish type: {fsd.fish_type}")
        print(f"Max biomass: {fsd.max_biomass_kg():.1f} kg")
        print(f"Max fish count: {fsd.max_fish_count()}")
        print(f"Current density (2000): {fsd.current_density_percent(2000):.2f}%")
        print(f"O2 demand: {fsd.oxygen_demand_kg_per_day(2000):.2f} kg/day")
        print(f"Feed req: {fsd.feed_requirement_kg_per_day(2000):.2f} kg/day")
        print(f"Stats: {fsd.stats()}")

if __name__ == "__main__":
    FishStockingDensity(0, 0, "tilapia", 0).run()
