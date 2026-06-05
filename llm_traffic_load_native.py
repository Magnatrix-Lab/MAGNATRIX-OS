"""Traffic Load Calculator — ESAL, axle load, pavement design, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class TrafficLoadCalculator:
    axle_loads: List[float] = field(default_factory=list)
    """kN per axle"""
    passes_per_year: int = 100000

    def esal_factor(self, axle_load: float, reference: float = 80.0) -> float:
        return (axle_load / reference) ** 4

    def total_esal(self) -> float:
        return sum(self.esal_factor(a) for a in self.axle_loads) * self.passes_per_year

    def design_esal(self, design_years: int = 20) -> float:
        return self.total_esal() * design_years

    def pavement_thickness(self, cbr: float = 5.0) -> float:
        esal = self.design_esal() / 1e6
        return 50 + 75 * math.log10(esal + 1) / (cbr ** 0.5) if cbr > 0 else 50

    def stats(self) -> Dict:
        return {"total_esal": round(self.total_esal(), 0), "design_esal": round(self.design_esal(), 0)}

def run():
    tlc = TrafficLoadCalculator([100, 80, 60, 40], 50000)
    print(tlc.stats())
    print("Thickness:", tlc.pavement_thickness(8))

if __name__ == "__main__":
    run()
