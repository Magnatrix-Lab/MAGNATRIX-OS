"""Blast Designer — powder factor, timing, fragmentation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class BlastDesigner:
    rock_density: float = 2.7
    hole_diameter: float = 0.15
    burden: float = 3.0
    spacing: float = 3.5
    bench_height: float = 10.0

    def hole_volume(self) -> float:
        r = self.hole_diameter / 2
        return math.pi * r ** 2 * self.bench_height

    def powder_factor(self, explosive_density: float = 1.2) -> float:
        rock_volume = self.burden * self.spacing * self.bench_height
        explosive_mass = self.hole_volume() * explosive_density
        return explosive_mass / rock_volume if rock_volume > 0 else 0.0

    def fragmentation_estimate(self, k50_factor: float = 0.8) -> float:
        pf = self.powder_factor()
        return k50_factor * (self.hole_diameter ** 0.8) / (pf ** 0.8) if pf > 0 else 0.0

    def timing_ms(self, vOD: float = 5000.0) -> float:
        return self.burden / vOD * 1000 if vOD > 0 else 0.0

    def pattern_efficiency(self) -> float:
        return min(1.0, (self.burden * self.spacing) / (self.bench_height ** 2))

    def stats(self) -> Dict:
        return {"powder_factor": round(self.powder_factor(), 3), "fragmentation": round(self.fragmentation_estimate(), 3), "timing_ms": round(self.timing_ms(), 1)}

def run():
    bd = BlastDesigner(burden=4, spacing=4.5, bench_height=12)
    print(bd.stats())

if __name__ == "__main__":
    run()
