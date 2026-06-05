"""Structural Analyzer — beams, trusses, moments, deflection, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Beam:
    length: float
    load: float
    elasticity: float = 200e9
    moment_of_inertia: float = 1e-6

    def max_moment(self) -> float:
        return self.load * self.length / 4

    def deflection(self) -> float:
        return self.load * self.length**3 / (48 * self.elasticity * self.moment_of_inertia)

    def stress(self, y: float) -> float:
        return self.max_moment() * y / self.moment_of_inertia

    def safety_factor(self, yield_strength: float) -> float:
        max_stress = self.stress(self.length / 10)
        return yield_strength / max_stress if max_stress > 0 else float('inf')

class StructuralAnalyzer:
    def __init__(self):
        self.beams: List[Beam] = []

    def add_beam(self, b: Beam):
        self.beams.append(b)

    def total_deflection(self) -> float:
        return sum(b.deflection() for b in self.beams)

    def critical_beam(self) -> Optional[Beam]:
        if not self.beams:
            return None
        return max(self.beams, key=lambda b: b.deflection())

    def stats(self) -> Dict:
        return {"beams": len(self.beams), "total_deflection": round(self.total_deflection(), 6)}

def run():
    sa = StructuralAnalyzer()
    sa.add_beam(Beam(5, 10000))
    sa.add_beam(Beam(3, 5000))
    print(sa.stats())
    cb = sa.critical_beam()
    if cb:
        print(f"Critical deflection: {cb.deflection():.6f} m")

if __name__ == "__main__":
    run()
