"""Crystal Growth — nucleation, growth rate, supercooling, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class CrystalGrowth:
    melting_point: float = 1000.0
    supercooling: float = 50.0
    growth_rate_constant: float = 1e-6
    diffusion_coeff: float = 1e-9

    def nucleation_rate(self, viscosity: float = 1.0) -> float:
        delta_t = self.supercooling
        return self.growth_rate_constant * math.exp(-1 / (delta_t ** 2)) / viscosity if delta_t > 0 else 0.0

    def growth_rate(self, undercooling: float) -> float:
        return self.growth_rate_constant * undercooling ** 2

    def crystal_size(self, time: float, undercooling: float) -> float:
        return self.growth_rate(undercooling) * time

    def facet_growth(self, m_index: int = 1) -> float:
        return self.growth_rate_constant * (1 + 0.1 * m_index)

    def stats(self, time: float = 3600) -> Dict:
        return {"nucleation": round(self.nucleation_rate(), 6), "size_1h": round(self.crystal_size(time, 30), 6), "growth_rate": round(self.growth_rate(30), 6)}

def run():
    cg = CrystalGrowth(melting_point=1200, supercooling=100, growth_rate_constant=1e-5)
    print(cg.stats())

if __name__ == "__main__":
    run()
