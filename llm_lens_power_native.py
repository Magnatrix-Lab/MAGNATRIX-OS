"""Lens Power Calculator — spherical, cylindrical, prismatic, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class LensPowerCalculator:
    front_radius: float = 0.0
    back_radius: float = 0.0
    thickness_mm: float = 2.0
    index: float = 1.5

    def lensmaker_power(self) -> float:
        n = self.index
        r1 = self.front_radius
        r2 = self.back_radius
        if r1 == 0 or r2 == 0:
            return 0.0
        return (n - 1) * (1/r1 - 1/r2)

    def effective_power(self, vertex_distance_m: float = 0.012) -> float:
        p = self.lensmaker_power()
        return p / (1 - vertex_distance_m * p) if (1 - vertex_distance_m * p) != 0 else p

    def prism_diopters(self, decentration_mm: float, power: float) -> float:
        return power * decentration_mm / 10

    def base_direction(self, prism: float, direction: str) -> Tuple[float, str]:
        return prism, direction

    def add_cylinder(self, sphere: float, cyl: float, axis: float, new_cyl: float, new_axis: float) -> Tuple[float, float, float]:
        if abs(axis - new_axis) < 5 or abs(abs(axis - new_axis) - 180) < 5:
            total_cyl = cyl + new_cyl
            return sphere, total_cyl, axis
        return sphere + cyl/2 + new_cyl/2, abs(cyl - new_cyl), (axis + new_axis) / 2

    def stats(self) -> Dict:
        return {"power_D": round(self.lensmaker_power(), 2), "effective_D": round(self.effective_power(), 2)}

def run():
    lpc = LensPowerCalculator(front_radius=0.1, back_radius=-0.1, index=1.5)
    print(lpc.stats())
    print("Prism 2mm decentration at 4D:", lpc.prism_diopters(2, 4))
    print("Add cyl:", lpc.add_cylinder(-2, -1, 180, -0.75, 180))

if __name__ == "__main__":
    run()
