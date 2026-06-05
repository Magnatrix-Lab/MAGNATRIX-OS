"""Native stdlib module: Tailings Dam Calculator
Calculates tailings volumes, dam heights, and storage capacities for mining.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class TailingsDamCalculator:
    annual_tailings_tonnes: float
    tailings_density_ton_m3: float
    dam_height_m: float
    dam_crest_width_m: float
    dam_slope_ratio: float
    impoundment_area_m2: float

    def annual_tailings_volume_m3(self) -> float:
        if self.tailings_density_ton_m3 == 0:
            return 0.0
        return self.annual_tailings_tonnes / self.tailings_density_ton_m3

    def dam_volume_m3(self) -> float:
        if self.dam_slope_ratio == 0:
            return 0.0
        base_width = self.dam_crest_width_m + 2 * self.dam_height_m * self.dam_slope_ratio
        return 0.5 * (self.dam_crest_width_m + base_width) * self.dam_height_m * self.impoundment_area_m2 / 10000

    def storage_capacity_m3(self) -> float:
        return self.impoundment_area_m2 * self.dam_height_m

    def years_to_fill(self) -> float:
        if self.annual_tailings_volume_m3() == 0:
            return 0.0
        return self.storage_capacity_m3() / self.annual_tailings_volume_m3()

    def freeboard_m(self, water_level_m: float) -> float:
        return self.dam_height_m - water_level_m

    def stats(self) -> Dict:
        return {
            "annual_tailings_m3": round(self.annual_tailings_volume_m3(), 1),
            "dam_volume_m3": round(self.dam_volume_m3(), 1),
            "storage_capacity_m3": round(self.storage_capacity_m3(), 1),
            "years_to_fill": round(self.years_to_fill(), 1),
            "freeboard_m": self.dam_height_m,
        }

def run():
    tdc = TailingsDamCalculator(annual_tailings_tonnes=2000000, tailings_density_ton_m3=1.8, dam_height_m=40, dam_crest_width_m=8, dam_slope_ratio=2.5, impoundment_area_m2=500000)
    print(tdc.stats())

if __name__ == "__main__":
    run()
