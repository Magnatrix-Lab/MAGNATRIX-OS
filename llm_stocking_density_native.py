"""Native stdlib module: Stocking Density Calculator
Calculates optimal stocking density for fish ponds and tanks.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class SystemType(Enum):
    POND = "pond"
    RAS = "ras"
    CAGE = "cage"
    TANK = "tank"

@dataclass
class StockingDensityCalculator:
    species: str
    volume_m3: float
    system_type: SystemType
    target_biomass_kg_per_m3: float
    avg_weight_g: float

    def max_biomass_kg(self) -> float:
        return self.volume_m3 * self.target_biomass_kg_per_m3

    def max_fish_count(self) -> int:
        if self.avg_weight_g == 0:
            return 0
        return int(self.max_biomass_kg() * 1000 / self.avg_weight_g)

    def current_density(self, current_fish_count: int) -> float:
        if self.volume_m3 == 0:
            return 0.0
        return (current_fish_count * self.avg_weight_g / 1000) / self.volume_m3

    def density_pct(self, current_fish_count: int) -> float:
        if self.max_fish_count() == 0:
            return 0.0
        return (current_fish_count / self.max_fish_count()) * 100

    def stats(self, current_fish_count: int = 0) -> Dict:
        return {
            "species": self.species,
            "system": self.system_type.value,
            "volume_m3": self.volume_m3,
            "max_biomass_kg": round(self.max_biomass_kg(), 1),
            "max_fish_count": self.max_fish_count(),
            "current_density": round(self.current_density(current_fish_count), 2) if current_fish_count else None,
            "density_pct": round(self.density_pct(current_fish_count), 1) if current_fish_count else None,
        }

def run():
    sd = StockingDensityCalculator(species="Tilapia", volume_m3=500, system_type=SystemType.POND, target_biomass_kg_per_m3=2.5, avg_weight_g=250)
    print(sd.stats(current_fish_count=4000))

if __name__ == "__main__":
    run()
