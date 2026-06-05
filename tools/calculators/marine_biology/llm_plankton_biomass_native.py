"""Native stdlib module: Plankton Biomass Calculator
Estimates plankton biomass, productivity, and trophic transfer efficiency.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class PlanktonBiomassCalculator:
    water_volume_m3: float
    chlorophyll_a_mg_m3: float
    phytoplankton_carbon_ratio: float = 50.0
    zooplankton_to_phytoplankton_ratio: float = 0.2

    def phytoplankton_carbon_mg_m3(self) -> float:
        return self.chlorophyll_a_mg_m3 * self.phytoplankton_carbon_ratio

    def total_phytoplankton_carbon_g(self) -> float:
        return self.phytoplankton_carbon_mg_m3() * self.water_volume_m3 / 1000

    def zooplankton_carbon_mg_m3(self) -> float:
        return self.phytoplankton_carbon_mg_m3() * self.zooplankton_to_phytoplankton_ratio

    def total_zooplankton_carbon_g(self) -> float:
        return self.zooplankton_carbon_mg_m3() * self.water_volume_m3 / 1000

    def primary_productivity_g_c_day(self, p_b_ratio: float = 1.0) -> float:
        return self.total_phytoplankton_carbon_g() * p_b_ratio

    def trophic_transfer_efficiency_pct(self, next_trophic_level_carbon_g: float) -> float:
        if self.total_zooplankton_carbon_g() == 0:
            return 0.0
        return (next_trophic_level_carbon_g / self.total_zooplankton_carbon_g()) * 100

    def stats(self, next_trophic_level_carbon_g: float = 0) -> Dict:
        return {
            "water_volume_m3": self.water_volume_m3,
            "chlorophyll_a_mg_m3": self.chlorophyll_a_mg_m3,
            "phytoplankton_carbon_g": round(self.total_phytoplankton_carbon_g(), 2),
            "zooplankton_carbon_g": round(self.total_zooplankton_carbon_g(), 2),
            "primary_productivity_g_c_day": round(self.primary_productivity_g_c_day(), 2),
            "trophic_efficiency_pct": round(self.trophic_transfer_efficiency_pct(next_trophic_level_carbon_g), 1) if next_trophic_level_carbon_g else None,
        }

def run():
    pbc = PlanktonBiomassCalculator(water_volume_m3=1000000, chlorophyll_a_mg_m3=2.5, phytoplankton_carbon_ratio=50, zooplankton_to_phytoplankton_ratio=0.2)
    print(pbc.stats(next_trophic_level_carbon_g=5000))

if __name__ == "__main__":
    run()
