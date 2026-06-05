"""Native stdlib module: Pulp Yield Calculator
Calculates pulp yields, kappa numbers, and delignification metrics for papermaking.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class WoodSpecies(Enum):
    PINE = "pine"
    SPRUCE = "spruce"
    EUCALYPTUS = "eucalyptus"
    BIRCH = "birch"
    ACACIA = "acacia"

class PulpingProcess(Enum):
    KRAFT = "kraft"
    SULFITE = "sulfite"
    SODA = "soda"
    MECHANICAL = "mechanical"
    CHEMITHERMOMECHANICAL = "chemithermomechanical"

@dataclass
class PulpYieldCalculator:
    wood_species: WoodSpecies
    pulping_process: PulpingProcess
    wood_chips_ton: float
    lignin_pct: float
    kappa_number: float

    def pulp_yield_pct(self) -> float:
        yields = {
            (WoodSpecies.PINE, PulpingProcess.KRAFT): 45,
            (WoodSpecies.SPRUCE, PulpingProcess.KRAFT): 46,
            (WoodSpecies.EUCALYPTUS, PulpingProcess.KRAFT): 48,
            (WoodSpecies.BIRCH, PulpingProcess.KRAFT): 44,
            (WoodSpecies.PINE, PulpingProcess.SULFITE): 50,
            (WoodSpecies.PINE, PulpingProcess.MECHANICAL): 92,
            (WoodSpecies.EUCALYPTUS, PulpingProcess.MECHANICAL): 90,
        }
        base = yields.get((self.wood_species, self.pulping_process), 45)
        if self.kappa_number > 30:
            base -= (self.kappa_number - 30) * 0.2
        return base

    def pulp_production_ton(self) -> float:
        return self.wood_chips_ton * (self.pulp_yield_pct() / 100)

    def lignin_removal_pct(self) -> float:
        if self.lignin_pct == 0:
            return 0.0
        residual_lignin = self.kappa_number * 0.15
        return ((self.lignin_pct - residual_lignin) / self.lignin_pct) * 100

    def bleach_chemical_demand_kg_ton(self) -> float:
        if self.kappa_number < 15:
            return 30
        elif self.kappa_number < 30:
            return 50
        return 80

    def stats(self) -> Dict:
        return {
            "wood_species": self.wood_species.value,
            "pulping_process": self.pulping_process.value,
            "pulp_yield_pct": round(self.pulp_yield_pct(), 1),
            "pulp_production_ton": round(self.pulp_production_ton(), 1),
            "lignin_removal_pct": round(self.lignin_removal_pct(), 1),
            "bleach_demand_kg_ton": self.bleach_chemical_demand_kg_ton(),
        }

def run():
    pyc = PulpYieldCalculator(wood_species=WoodSpecies.PINE, pulping_process=PulpingProcess.KRAFT, wood_chips_ton=100, lignin_pct=27, kappa_number=28)
    print(pyc.stats())

if __name__ == "__main__":
    run()
