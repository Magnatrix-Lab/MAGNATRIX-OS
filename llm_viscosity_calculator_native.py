"""Viscosity Calculator — shear, temperature, thickener, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class ViscosityCalculator:
    base_viscosity: float = 1.0
    thickener_pct: float = 0.0
    temperature: float = 25.0
    reference_temp: float = 25.0

    def viscosity(self) -> float:
        thick = self.base_viscosity * (1 + self.thickener_pct * 2)
        temp_factor = math.exp(-0.02 * (self.temperature - self.reference_temp))
        return thick * temp_factor

    def shear_thinning(self, shear_rate: float, n: float = 0.8) -> float:
        base = self.viscosity()
        return base * (shear_rate ** (n - 1))

    def yield_stress(self, k: float = 0.1) -> float:
        return k * self.thickener_pct

    def pumpable(self, max_viscosity: float = 5000) -> bool:
        return self.viscosity() <= max_viscosity

    def stats(self) -> Dict:
        return {"viscosity": round(self.viscosity(), 2), "yield_stress": round(self.yield_stress(), 3), "pumpable": self.pumpable()}

def run():
    vc = ViscosityCalculator(base_viscosity=100, thickener_pct=1.5, temperature=40)
    print(vc.stats())
    print("Shear thinning at 100/s:", vc.shear_thinning(100))

if __name__ == "__main__":
    run()
