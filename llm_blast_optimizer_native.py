"""Blast Optimizer — fragmentation, powder factor, vibration, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class BlastOptimizer:
    hole_diameter: float = 150.0
    burden: float = 4.0
    spacing: float = 5.0
    bench_height: float = 10.0
    explosive_density: float = 1.2

    def hole_volume(self) -> float:
        r = self.hole_diameter / 2000
        return math.pi * r * r * self.bench_height

    def explosive_per_hole(self) -> float:
        return self.hole_volume() * self.explosive_density

    def powder_factor(self) -> float:
        rock_volume = self.burden * self.spacing * self.bench_height
        return self.explosive_per_hole() / rock_volume if rock_volume > 0 else 0.0

    def fragmentation_size(self, kuz_ram_a: float = 7.0, kuz_ram_b: float = 0.8) -> float:
        pf = self.powder_factor()
        if pf <= 0:
            return 0.0
        return kuz_ram_a * pf ** -kuz_ram_b

    def vibration_ppv(self, distance: float, k: float = 1000, b: float = -1.5) -> float:
        charge = self.explosive_per_hole()
        return k * (distance / charge ** 0.5) ** b if charge > 0 and distance > 0 else 0.0

    def stats(self) -> Dict:
        return {"explosive_per_hole": round(self.explosive_per_hole(), 1), "powder_factor": round(self.powder_factor(), 3), "fragment_size": round(self.fragmentation_size(), 2)}

def run():
    bo = BlastOptimizer()
    print(bo.stats())
    print("PPV at 500m:", bo.vibration_ppv(500))

if __name__ == "__main__":
    run()
