"""Native stdlib module: Flooring Calculator
Calculates flooring material, underlay, and wastage for room installations.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class FlooringType(Enum):
    HARDWOOD = "hardwood"
    LAMINATE = "laminate"
    TILE = "tile"
    CARPET = "carpet"
    VINYL = "vinyl"

@dataclass
class FlooringCalculator:
    room_name: str
    length_m: float
    width_m: float
    flooring_type: FlooringType
    plank_width_m: float = 0.12
    plank_length_m: float = 1.2
    wastage_pct: float = 10.0
    cost_per_m2: float = 30.0

    def room_area_m2(self) -> float:
        return self.length_m * self.width_m

    def planks_needed(self) -> int:
        if self.plank_width_m == 0 or self.plank_length_m == 0:
            return 0
        plank_area = self.plank_width_m * self.plank_length_m
        area_with_wastage = self.room_area_m2() * (1 + self.wastage_pct / 100)
        return int(area_with_wastage / plank_area) + 1

    def total_material_cost(self) -> float:
        return self.room_area_m2() * (1 + self.wastage_pct / 100) * self.cost_per_m2

    def underlay_needed_m2(self) -> float:
        return self.room_area_m2() * 1.05

    def perimeter_m(self) -> float:
        return 2 * (self.length_m + self.width_m)

    def skirting_length_m(self) -> float:
        return self.perimeter_m()

    def stats(self) -> Dict:
        return {
            "room": self.room_name,
            "area_m2": round(self.room_area_m2(), 2),
            "flooring_type": self.flooring_type.value,
            "planks_needed": self.planks_needed(),
            "material_cost": round(self.total_material_cost(), 2),
            "underlay_m2": round(self.underlay_needed_m2(), 1),
            "skirting_m": round(self.skirting_length_m(), 1),
        }

def run():
    fc = FlooringCalculator(room_name="Bedroom", length_m=4.5, width_m=3.5, flooring_type=FlooringType.LAMINATE, plank_width_m=0.19, plank_length_m=1.28, cost_per_m2=25)
    print(fc.stats())

if __name__ == "__main__":
    run()
