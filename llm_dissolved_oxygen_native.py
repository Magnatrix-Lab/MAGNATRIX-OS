"""Native stdlib module: Dissolved Oxygen Calculator
Estimates dissolved oxygen requirements and aeration needs for aquaculture.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class SpeciesType(Enum):
    WARM_WATER = "warm_water"
    COLD_WATER = "cold_water"
    SHELLFISH = "shellfish"

@dataclass
class DissolvedOxygenCalculator:
    species_type: SpeciesType
    volume_m3: float
    stock_biomass_kg: float
    temperature_c: float
    current_do_mg_l: float

    def minimum_do_mg_l(self) -> float:
        thresholds = {SpeciesType.WARM_WATER: 4.0, SpeciesType.COLD_WATER: 6.0, SpeciesType.SHELLFISH: 5.0}
        return thresholds.get(self.species_type, 4.0)

    def do_deficit_mg_l(self) -> float:
        return max(0, self.minimum_do_mg_l() - self.current_do_mg_l)

    def oxygen_demand_kg_h(self) -> float:
        return self.stock_biomass_kg * 0.005

    def aeration_required_kg_o2_h(self) -> float:
        if self.do_deficit_mg_l() > 0:
            return self.oxygen_demand_kg_h() * 1.5
        return self.oxygen_demand_kg_h()

    def oxygen_status(self) -> str:
        if self.current_do_mg_l < self.minimum_do_mg_l() * 0.5:
            return "critical"
        elif self.current_do_mg_l < self.minimum_do_mg_l():
            return "low"
        return "adequate"

    def stats(self) -> Dict:
        return {
            "species_type": self.species_type.value,
            "minimum_do": self.minimum_do_mg_l(),
            "current_do": self.current_do_mg_l,
            "do_deficit": round(self.do_deficit_mg_l(), 2),
            "oxygen_demand_kg_h": round(self.oxygen_demand_kg_h(), 3),
            "aeration_required_kg_h": round(self.aeration_required_kg_o2_h(), 3),
            "status": self.oxygen_status(),
        }

def run():
    do = DissolvedOxygenCalculator(species_type=SpeciesType.COLD_WATER, volume_m3=1000, stock_biomass_kg=5000, temperature_c=12, current_do_mg_l=5.5)
    print(do.stats())

if __name__ == "__main__":
    run()
