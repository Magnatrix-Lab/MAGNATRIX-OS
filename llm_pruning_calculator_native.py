"""Pruning Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PruningCalculator:
    tree_count: int
    tree_height_m: float
    tree_canopy_diameter_m: float
    pruning_percent: float = 20.0
    labor_time_min_per_tree: float = 15.0

    def biomass_removed_kg(self) -> float:
        canopy_area = math.pi * (self.tree_canopy_diameter_m / 2) ** 2
        biomass = canopy_area * self.tree_height_m * 0.5
        return round(biomass * self.pruning_percent / 100.0, 2)

    def total_labor_hours(self) -> float:
        return round(self.tree_count * self.labor_time_min_per_tree / 60.0, 2)

    def labor_cost(self, hourly_rate: float = 15.0) -> float:
        return round(self.total_labor_hours() * hourly_rate, 2)

    def disposal_volume_m3(self) -> float:
        biomass = self.biomass_removed_kg()
        return round(biomass * 0.003, 3)

    def tool_sharpening_frequency(self) -> int:
        return max(1, int(self.tree_count / 50))

    def stats(self) -> Dict[str, float]:
        return {
            "biomass_removed_kg": self.biomass_removed_kg(),
            "total_labor_hours": self.total_labor_hours(),
            "disposal_volume_m3": self.disposal_volume_m3(),
        }

    def run(self):
        print("=" * 60)
        print("PRUNING CALCULATOR")
        print("=" * 60)
        pr = PruningCalculator(
            tree_count=50, tree_height_m=3.5, tree_canopy_diameter_m=2.5,
            pruning_percent=25, labor_time_min_per_tree=20
        )
        print(f"Trees: {pr.tree_count}, Height: {pr.tree_height_m} m")
        print(f"Biomass removed: {pr.biomass_removed_kg():.2f} kg")
        print(f"Labor: {pr.total_labor_hours():.2f} hours")
        print(f"Labor cost: ${pr.labor_cost():.2f}")
        print(f"Disposal: {pr.disposal_volume_m3():.3f} m3")
        print(f"Sharpening: every {pr.tool_sharpening_frequency()} trees")
        print(f"Stats: {pr.stats()}")

if __name__ == "__main__":
    PruningCalculator(0, 0, 0).run()
