"""Biomass Calculator — above-ground, below-ground, carbon, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class BiomassCalculator:
    dbh_cm: float = 30.0
    height_m: float = 20.0
    wood_density: float = 0.5
    species: str = "generic"

    def above_ground_biomass(self) -> float:
        """Chave et al. pan-tropical"""
        return 0.0673 * (self.wood_density * self.dbh_cm**2 * self.height_m)**0.976

    def below_ground_biomass(self, ratio: float = 0.2) -> float:
        return self.above_ground_biomass() * ratio

    def total_biomass(self) -> float:
        return self.above_ground_biomass() + self.below_ground_biomass()

    def carbon_stock(self, carbon_fraction: float = 0.47) -> float:
        return self.total_biomass() * carbon_fraction

    def co2_equivalent(self) -> float:
        return self.carbon_stock() * 44 / 12

    def stats(self) -> Dict:
        return {"agb": round(self.above_ground_biomass(), 2), "total": round(self.total_biomass(), 2), "carbon": round(self.carbon_stock(), 2), "co2": round(self.co2_equivalent(), 2)}

def run():
    bc = BiomassCalculator(dbh_cm=40, height_m=25, wood_density=0.6)
    print(bc.stats())

if __name__ == "__main__":
    run()
