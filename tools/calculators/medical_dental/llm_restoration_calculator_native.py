"""Native stdlib module: Restoration Calculator
Calculates dental restoration material needs and cost estimates.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class RestorationType(Enum):
    FILLING = "filling"
    CROWN = "crown"
    BRIDGE = "bridge"
    IMPLANT = "implant"
    VENEER = "veneer"

class MaterialType(Enum):
    AMALGAM = "amalgam"
    COMPOSITE = "composite"
    CERAMIC = "ceramic"
    GOLD = "gold"
    ZIRCONIA = "zirconia"

@dataclass
class RestorationCalculator:
    restoration_type: RestorationType
    material: MaterialType
    num_surfaces: int
    tooth_number: int
    base_cost: float

    def material_multiplier(self) -> float:
        multipliers = {
            MaterialType.AMALGAM: 1.0,
            MaterialType.COMPOSITE: 1.5,
            MaterialType.CERAMIC: 2.5,
            MaterialType.GOLD: 4.0,
            MaterialType.ZIRCONIA: 3.5,
        }
        return multipliers.get(self.material, 1.0)

    def surface_multiplier(self) -> float:
        if self.num_surfaces == 1:
            return 1.0
        elif self.num_surfaces == 2:
            return 1.3
        elif self.num_surfaces == 3:
            return 1.6
        return 2.0

    def type_multiplier(self) -> float:
        multipliers = {
            RestorationType.FILLING: 1.0,
            RestorationType.CROWN: 5.0,
            RestorationType.BRIDGE: 8.0,
            RestorationType.IMPLANT: 15.0,
            RestorationType.VENEER: 6.0,
        }
        return multipliers.get(self.restoration_type, 1.0)

    def total_cost(self) -> float:
        return self.base_cost * self.material_multiplier() * self.surface_multiplier() * self.type_multiplier()

    def estimated_time_min(self) -> int:
        times = {
            RestorationType.FILLING: 30,
            RestorationType.CROWN: 60,
            RestorationType.BRIDGE: 90,
            RestorationType.IMPLANT: 120,
            RestorationType.VENEER: 45,
        }
        return times.get(self.restoration_type, 30)

    def stats(self) -> Dict:
        return {
            "restoration": self.restoration_type.value,
            "material": self.material.value,
            "tooth": self.tooth_number,
            "surfaces": self.num_surfaces,
            "base_cost": self.base_cost,
            "total_cost": round(self.total_cost(), 2),
            "estimated_time_min": self.estimated_time_min(),
        }

def run():
    rc = RestorationCalculator(restoration_type=RestorationType.FILLING, material=MaterialType.COMPOSITE, num_surfaces=2, tooth_number=14, base_cost=100)
    print(rc.stats())

if __name__ == "__main__":
    run()
