"""Native stdlib module: Sett Calculator
Calculates ends per inch, denting, reed size, and warp density for weaving.
"""
from dataclasses import dataclass
from typing import Dict, Optional
import math

@dataclass
class SettCalculator:
    yarn_diameter_mm: float
    desired_weave_structure: str  # plain, twill, satin, basket, lace
    fabric_width_in: float = 20.0

    _SETT_MULTIPLIERS = {
        "plain": 0.7, "twill": 0.8, "satin": 0.85, "basket": 0.6, "lace": 0.5,
    }

    def ends_per_inch(self) -> float:
        if self.yarn_diameter_mm == 0:
            return 0
        multiplier = self._SETT_MULTIPLIERS.get(self.desired_weave_structure, 0.7)
        return (25.4 / self.yarn_diameter_mm) * multiplier

    def ends_per_cm(self) -> float:
        return self.ends_per_inch() / 2.54

    def total_ends(self) -> int:
        return math.ceil(self.ends_per_inch() * self.fabric_width_in)

    def reed_size_recommended(self) -> int:
        epi = self.ends_per_inch()
        if epi <= 6:
            return 6
        elif epi <= 8:
            return 8
        elif epi <= 10:
            return 10
        elif epi <= 12:
            return 12
        elif epi <= 15:
            return 15
        elif epi <= 20:
            return 20
        elif epi <= 25:
            return 25
        return 30

    def denting(self, ends_per_dent: int = 2) -> str:
        epi = self.ends_per_inch()
        reed = self.reed_size_recommended()
        if reed == 0:
            return "0"
        dents_per_inch = epi / ends_per_dent
        ratio = dents_per_inch / reed
        return f"{ends_per_dent} in {ratio:.1f} dents"

    def warp_width_in(self) -> float:
        return self.fabric_width_in * 1.1

    def stats(self, ends_per_dent: int = 2) -> Dict:
        return {
            "yarn_diameter_mm": self.yarn_diameter_mm,
            "weave_structure": self.desired_weave_structure,
            "ends_per_inch": round(self.ends_per_inch(), 1),
            "ends_per_cm": round(self.ends_per_cm(), 1),
            "total_ends": self.total_ends(),
            "reed_size_recommended": self.reed_size_recommended(),
            "denting": self.denting(ends_per_dent),
            "warp_width_in": round(self.warp_width_in(), 1),
        }

def run():
    sc = SettCalculator(yarn_diameter_mm=0.5, desired_weave_structure="twill", fabric_width_in=24)
    print(sc.stats())

if __name__ == "__main__":
    run()
