"""Aerodynamics Calculator — lift, drag, Reynolds, Mach, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class Aerodynamics:
    velocity: float = 100.0
    chord: float = 2.0
    rho: float = 1.225
    viscosity: float = 1.46e-5
    cl: float = 0.5
    cd: float = 0.03

    def reynolds(self) -> float:
        return self.rho * self.velocity * self.chord / self.viscosity

    def mach(self, speed_of_sound: float = 343) -> float:
        return self.velocity / speed_of_sound

    def lift(self, area: float) -> float:
        return 0.5 * self.rho * self.velocity**2 * area * self.cl

    def drag(self, area: float) -> float:
        return 0.5 * self.rho * self.velocity**2 * area * self.cd

    def l_d_ratio(self) -> float:
        return self.cl / self.cd if self.cd > 0 else 0.0

    def compressible_correction(self) -> float:
        m = self.mach()
        if m < 0.3:
            return 1.0
        return 1 / math.sqrt(1 - m**2)

    def stats(self, area: float = 10) -> Dict:
        return {"reynolds": f"{self.reynolds():.2e}", "mach": round(self.mach(), 3), "lift_N": round(self.lift(area), 0), "ld_ratio": round(self.l_d_ratio(), 1)}

def run():
    a = Aerodynamics(velocity=250, cl=0.6, cd=0.025)
    print(a.stats(20))
    print("Compressible:", a.compressible_correction())

if __name__ == "__main__":
    run()
