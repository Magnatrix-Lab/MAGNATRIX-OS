"""Native stdlib module: Clay Body Calculator
Formulates clay bodies, calculates shrinkage, absorption, and recipes.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ClayBodyCalculator:
    clay_parts: float
    feldspar_parts: float
    silica_parts: float
    water_content_pct: float = 20.0

    def total_parts(self) -> float:
        return self.clay_parts + self.feldspar_parts + self.silica_parts

    def clay_pct(self) -> float:
        return (self.clay_parts / self.total_parts()) * 100 if self.total_parts() else 0

    def feldspar_pct(self) -> float:
        return (self.feldspar_parts / self.total_parts()) * 100 if self.total_parts() else 0

    def silica_pct(self) -> float:
        return (self.silica_parts / self.total_parts()) * 100 if self.total_parts() else 0

    def drying_shrinkage_pct(self, base_shrinkage: float = 6.0) -> float:
        return base_shrinkage * (1 + (self.water_content_pct - 20) * 0.02)

    def firing_shrinkage_pct(self, base_shrinkage: float = 8.0) -> float:
        return base_shrinkage * (1 + (self.water_content_pct - 20) * 0.015)

    def total_shrinkage_pct(self) -> float:
        d = self.drying_shrinkage_pct()
        f = self.firing_shrinkage_pct()
        return d + f - (d * f / 100)

    def absorption_pct(self, porosity: float = 15.0) -> float:
        return porosity * (1 - self.firing_shrinkage_pct() / 100)

    def stats(self) -> Dict:
        return {
            "clay_pct": round(self.clay_pct(), 1),
            "feldspar_pct": round(self.feldspar_pct(), 1),
            "silica_pct": round(self.silica_pct(), 1),
            "drying_shrinkage_pct": round(self.drying_shrinkage_pct(), 1),
            "firing_shrinkage_pct": round(self.firing_shrinkage_pct(), 1),
            "total_shrinkage_pct": round(self.total_shrinkage_pct(), 1),
            "absorption_pct": round(self.absorption_pct(), 1),
        }

def run():
    cbc = ClayBodyCalculator(clay_parts=50, feldspar_parts=25, silica_parts=25, water_content_pct=22)
    print(cbc.stats())

if __name__ == "__main__":
    run()
