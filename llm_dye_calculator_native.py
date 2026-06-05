"""Native stdlib module: Dye Calculator
Calculates dye quantities, shade depths, and color matching recipes.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class ShadeDepth(Enum):
    PALE = 0.5
    LIGHT = 1.0
    MEDIUM = 2.0
    DARK = 4.0
    HEAVY = 6.0

@dataclass
class DyeCalculator:
    fabric_weight_kg: float
    shade_depth: ShadeDepth
    dye_concentration_pct: float = 2.0
    liquor_ratio: float = 10.0
    salt_g_per_l: float = 50.0
    soda_ash_g_per_l: float = 20.0

    def dye_required_g(self) -> float:
        return self.fabric_weight_kg * 1000 * (self.dye_concentration_pct / 100) * self.shade_depth.value

    def liquor_volume_l(self) -> float:
        return self.fabric_weight_kg * self.liquor_ratio

    def salt_required_g(self) -> float:
        return self.liquor_volume_l() * self.salt_g_per_l

    def soda_ash_required_g(self) -> float:
        return self.liquor_volume_l() * self.soda_ash_g_per_l

    def stats(self) -> Dict:
        return {
            "fabric_kg": self.fabric_weight_kg,
            "shade_depth": self.shade_depth.name,
            "dye_g": round(self.dye_required_g(), 1),
            "liquor_volume_l": round(self.liquor_volume_l(), 1),
            "salt_g": round(self.salt_required_g(), 1),
            "soda_ash_g": round(self.soda_ash_required_g(), 1),
        }

def run():
    dc = DyeCalculator(fabric_weight_kg=50, shade_depth=ShadeDepth.MEDIUM, dye_concentration_pct=2.5, liquor_ratio=12)
    print(dc.stats())

if __name__ == "__main__":
    run()
