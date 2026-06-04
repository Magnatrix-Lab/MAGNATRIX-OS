"""Band Gap Calculator — Kronig-Penney, DOS, semiconductor, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math, cmath

@dataclass
class BandGapCalculator:
    lattice_constant: float = 1.0
    potential_height: float = 10.0
    potential_width: float = 0.1
    effective_mass: float = 0.067
    """in units of electron mass"""

    def kronig_penney(self, k: float, E: float) -> float:
        a = self.lattice_constant
        b = self.potential_width
        V0 = self.potential_height
        alpha = cmath.sqrt(2j * (E - V0)) if E < V0 else cmath.sqrt(2 * (E - V0))
        beta = cmath.sqrt(2 * E)
        if abs(alpha) < 1e-10 or abs(beta) < 1e-10:
            return 0.0
        lhs = (beta**2 + alpha**2) / (2 * alpha * beta) * math.sinh(alpha * b) * math.sin(beta * (a - b)) + math.cosh(alpha * b) * math.cos(beta * (a - b))
        return abs(lhs - math.cos(k * a))

    def allowed_energies(self, num_k: int = 50) -> List[float]:
        energies = []
        for i in range(num_k):
            k = math.pi * i / num_k
            for E in [j * 0.1 for j in range(1, 200)]:
                if self.kronig_penney(k, E) < 0.5:
                    energies.append(E)
        return sorted(set(round(e, 2) for e in energies))

    def effective_gap(self, conduction: float, valence: float) -> float:
        return conduction - valence

    def stats(self) -> Dict:
        return {"a": self.lattice_constant, "V0": self.potential_height, "meff": self.effective_mass}

def run():
    bg = BandGapCalculator()
    e = bg.allowed_energies(20)
    print("Energies:", e[:10])
    print(bg.stats())

if __name__ == "__main__":
    run()
