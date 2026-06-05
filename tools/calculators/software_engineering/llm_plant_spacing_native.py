"""Plant Spacing Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PlantSpacing:
    row_spacing_m: float
    plant_spacing_m: float
    area_ha: float

    def plants_per_ha(self) -> int:
        if self.row_spacing_m <= 0 or self.plant_spacing_m <= 0:
            return 0
        return int(10000 / (self.row_spacing_m * self.plant_spacing_m))

    def total_plants(self) -> int:
        return int(self.plants_per_ha() * self.area_ha)

    def plants_per_row(self, row_length_m: float = 100.0) -> int:
        if self.plant_spacing_m <= 0:
            return 0
        return int(row_length_m / self.plant_spacing_m)

    def rows_per_field(self, field_width_m: float = 100.0) -> int:
        if self.row_spacing_m <= 0:
            return 0
        return int(field_width_m / self.row_spacing_m)

    def canopy_coverage_percent(self, plant_canopy_diameter_m: float = 0.5) -> float:
        area_per_plant = self.row_spacing_m * self.plant_spacing_m
        canopy_area = math.pi * (plant_canopy_diameter_m / 2) ** 2
        if area_per_plant <= 0:
            return 0.0
        return round(min(canopy_area / area_per_plant * 100, 100), 2)

    def stats(self) -> Dict[str, float]:
        return {
            "plants_per_ha": self.plants_per_ha(),
            "total_plants": self.total_plants(),
            "canopy_coverage_percent": self.canopy_coverage_percent(),
        }

    def run(self):
        print("=" * 60)
        print("PLANT SPACING CALCULATOR")
        print("=" * 60)
        ps = PlantSpacing(row_spacing_m=0.75, plant_spacing_m=0.30, area_ha=2)
        print(f"Row spacing: {ps.row_spacing_m} m")
        print(f"Plant spacing: {ps.plant_spacing_m} m")
        print(f"Plants/ha: {ps.plants_per_ha()}")
        print(f"Total plants: {ps.total_plants()}")
        print(f"Plants/row (100m): {ps.plants_per_row()}")
        print(f"Rows/field (100m): {ps.rows_per_field()}")
        print(f"Canopy coverage: {ps.canopy_coverage_percent():.2f}%")
        print(f"Stats: {ps.stats()}")

if __name__ == "__main__":
    PlantSpacing(0, 0, 0).run()
