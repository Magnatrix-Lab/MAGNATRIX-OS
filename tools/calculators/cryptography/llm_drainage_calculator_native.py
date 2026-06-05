"""Drainage Calculator — runoff, Manning, culvert sizing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class DrainageCalculator:
    area_hectares: float = 10.0
    rainfall_intensity: float = 50.0
    """mm/hr"""
    runoff_coefficient: float = 0.5

    def peak_runoff(self) -> float:
        return self.runoff_coefficient * self.rainfall_intensity * self.area_hectares / 360

    def manning_velocity(self, n: float, R: float, S: float) -> float:
        return (1 / n) * R ** (2/3) * S ** 0.5 if n > 0 else 0.0

    def culvert_capacity(self, diameter: float, n: float = 0.013, slope: float = 0.01) -> float:
        r = diameter / 2
        area = math.pi * r ** 2
        v = self.manning_velocity(n, r / 2, slope)
        return area * v

    def required_diameter(self, safety_factor: float = 1.5) -> float:
        q = self.peak_runoff() * safety_factor
        for d in range(100, 3000, 50):
            if self.culvert_capacity(d / 1000) >= q:
                return d / 1000
        return 3.0

    def stats(self) -> Dict:
        return {"runoff_m3s": round(self.peak_runoff(), 3), "required_dia": round(self.required_diameter(), 3)}

def run():
    dc = DrainageCalculator(area_hectares=25, rainfall_intensity=80, runoff_coefficient=0.7)
    print(dc.stats())

if __name__ == "__main__":
    run()
