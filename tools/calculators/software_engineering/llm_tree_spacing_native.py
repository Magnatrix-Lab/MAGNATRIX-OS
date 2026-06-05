"""Native stdlib module: Tree Spacing Calculator
Calculates optimal tree spacing, stand density, and basal area for forests.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class TreeSpacingCalculator:
    spacing_m: float
    total_area_ha: float
    avg_dbh_cm: float
    avg_height_m: float

    def trees_per_ha(self) -> int:
        return int(10000 / (self.spacing_m ** 2))

    def total_trees(self) -> int:
        return int(self.trees_per_ha() * self.total_area_ha)

    def basal_area_m2_per_ha(self) -> float:
        radius_m = (self.avg_dbh_cm / 100) / 2
        tree_ba = math.pi * (radius_m ** 2)
        return tree_ba * self.trees_per_ha()

    def stand_density_index(self) -> float:
        if self.avg_dbh_cm == 0:
            return 0.0
        return self.trees_per_ha() * (self.avg_dbh_cm / 25) ** 1.605

    def crown_cover_pct(self, crown_width_m: float) -> float:
        crown_area = math.pi * (crown_width_m / 2) ** 2
        plot_area = 10000 / self.trees_per_ha()
        return (crown_area / plot_area) * 100

    def volume_estimate_m3_per_ha(self) -> float:
        return self.basal_area_m2_per_ha() * self.avg_height_m * 0.5

    def stats(self) -> Dict:
        return {
            "trees_per_ha": self.trees_per_ha(),
            "total_trees": self.total_trees(),
            "basal_area_m2_ha": round(self.basal_area_m2_per_ha(), 2),
            "stand_density_index": round(self.stand_density_index(), 1),
            "volume_estimate_m3_ha": round(self.volume_estimate_m3_per_ha(), 1),
        }

def run():
    tsc = TreeSpacingCalculator(spacing_m=3, total_area_ha=50, avg_dbh_cm=25, avg_height_m=18)
    print(tsc.stats())

if __name__ == "__main__":
    run()
