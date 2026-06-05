"""Native stdlib module: Vitrification Calculator
Calculates vitrification temperature, porosity, and absorption for ceramics.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class ClayType(Enum):
    EARTHENWARE = "earthenware"
    STONEWARE = "stoneware"
    PORCELAIN = "porcelain"
    BONE_CHINA = "bone_china"
    TERRACOTTA = "terracotta"

@dataclass
class VitrificationCalculator:
    clay_type: ClayType
    firing_temp_c: float
    particle_size_um: float
    plasticity_index: float
    green_density_g_cm3: float

    def vitrification_temp_c(self) -> float:
        temps = {ClayType.EARTHENWARE: 1100, ClayType.STONEWARE: 1200, ClayType.PORCELAIN: 1300, ClayType.BONE_CHINA: 1250, ClayType.TERRACOTTA: 1050}
        return temps.get(self.clay_type, 1200)

    def vitrification_complete(self) -> bool:
        return self.firing_temp_c >= self.vitrification_temp_c()

    def water_absorption_pct(self) -> float:
        if self.vitrification_complete():
            return 0.5
        elif self.firing_temp_c > self.vitrification_temp_c() - 100:
            return 2.0
        return 8.0 + max(0, (self.vitrification_temp_c() - self.firing_temp_c) / 10)

    def porosity_pct(self) -> float:
        if self.vitrification_complete():
            return 0.5
        return max(0, 15 - (self.firing_temp_c - 1000) * 0.03)

    def bulk_density_g_cm3(self) -> float:
        if self.vitrification_complete():
            return 2.4
        return self.green_density_g_cm3 * (1 + (self.firing_temp_c - 1000) * 0.001)

    def linear_shrinkage_pct(self) -> float:
        base = {ClayType.EARTHENWARE: 8, ClayType.STONEWARE: 10, ClayType.PORCELAIN: 14, ClayType.BONE_CHINA: 12, ClayType.TERRACOTTA: 6}
        return base.get(self.clay_type, 10)

    def stats(self) -> Dict:
        return {
            "clay_type": self.clay_type.value,
            "firing_temp_c": self.firing_temp_c,
            "vitrification_temp_c": self.vitrification_temp_c(),
            "vitrification_complete": self.vitrification_complete(),
            "water_absorption_pct": round(self.water_absorption_pct(), 1),
            "porosity_pct": round(self.porosity_pct(), 1),
            "bulk_density": round(self.bulk_density_g_cm3(), 2),
            "linear_shrinkage_pct": self.linear_shrinkage_pct(),
        }

def run():
    vc = VitrificationCalculator(clay_type=ClayType.STONEWARE, firing_temp_c=1220, particle_size_um=20, plasticity_index=15, green_density_g_cm3=1.8)
    print(vc.stats())

if __name__ == "__main__":
    run()
