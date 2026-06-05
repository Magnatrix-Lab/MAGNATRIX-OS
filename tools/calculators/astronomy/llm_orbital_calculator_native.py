"""Orbital Calculator — Kepler, orbital elements, position, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class OrbitalCalculator:
    mu: float = 398600.4418
    """km^3/s^2 for Earth"""

    def orbital_period(self, a: float) -> float:
        return 2 * math.pi * math.sqrt(a**3 / self.mu)

    def velocity(self, r: float, a: float) -> float:
        return math.sqrt(self.mu * (2/r - 1/a))

    def kepler_equation(self, M: float, e: float, tol: float = 1e-8) -> float:
        E = M
        for _ in range(100):
            delta = (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
            E -= delta
            if abs(delta) < tol:
                break
        return E

    def true_anomaly(self, E: float, e: float) -> float:
        return 2 * math.atan2(math.sqrt(1 + e) * math.sin(E / 2), math.sqrt(1 - e) * math.cos(E / 2))

    def position(self, a: float, e: float, i: float, omega: float, w: float, M: float) -> Tuple[float, float, float]:
        E = self.kepler_equation(M, e)
        r = a * (1 - e * math.cos(E))
        nu = self.true_anomaly(E, e)
        x = r * (math.cos(omega) * math.cos(w + nu) - math.sin(omega) * math.sin(w + nu) * math.cos(i))
        y = r * (math.sin(omega) * math.cos(w + nu) + math.cos(omega) * math.sin(w + nu) * math.cos(i))
        z = r * math.sin(i) * math.sin(w + nu)
        return x, y, z

    def stats(self, a: float, e: float) -> Dict:
        return {"period": self.orbital_period(a), "periapsis": a*(1-e), "apoapsis": a*(1+e)}

def run():
    oc = OrbitalCalculator()
    print("Period LEO:", oc.orbital_period(6678))
    print("Vel ISS:", oc.velocity(6678, 6678))
    print(oc.stats(6678, 0.01))

if __name__ == "__main__":
    run()
