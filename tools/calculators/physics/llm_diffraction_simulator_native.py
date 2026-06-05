"""Diffraction Simulator — Bragg, structure factor, powder pattern, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math, cmath

@dataclass
class DiffractionSimulator:
    wavelength: float = 1.54
    atoms: List[Tuple[str, float, float, float]] = field(default_factory=list)
    """element, x, y, z fractional"""

    def bragg_angle(self, d: float) -> float:
        if d <= 0 or self.wavelength / (2 * d) > 1:
            return 0.0
        return math.degrees(math.asin(self.wavelength / (2 * d)))

    def structure_factor(self, h: int, k: int, l: int) -> complex:
        f = 0+0j
        for element, x, y, z in self.atoms:
            phase = 2 * math.pi * (h*x + k*y + l*z)
            f += cmath.exp(1j * phase)
        return f

    def intensity(self, h: int, k: int, l: int) -> float:
        f = self.structure_factor(h, k, l)
        return abs(f)**2

    def powder_pattern(self, hkl_list: List[Tuple[int, int, int]], a: float) -> List[Tuple[float, float]]:
        pattern = []
        for h, k, l in hkl_list:
            d = a / math.sqrt(h*h + k*k + l*l)
            theta = self.bragg_angle(d)
            i = self.intensity(h, k, l)
            pattern.append((2*theta, i))
        return pattern

    def stats(self) -> Dict:
        return {"wavelength": self.wavelength, "atoms": len(self.atoms)}

def run():
    ds = DiffractionSimulator(atoms=[("Cu",0,0,0),("Cu",0.5,0.5,0),("Cu",0.5,0,0.5),("Cu",0,0.5,0.5)])
    print("I(111):", ds.intensity(1,1,1))
    print("2theta(111):", ds.bragg_angle(2.09))
    print(ds.stats())

if __name__ == "__main__":
    run()
