"""Refraction Calculator — sphere, cylinder, axis, prism, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class RefractionCalculator:
    sphere_od: float = 0.0
    cyl_od: float = 0.0
    axis_od: float = 0.0
    sphere_os: float = 0.0
    cyl_os: float = 0.0
    axis_os: float = 0.0

    def spherical_equivalent(self, sphere: float, cyl: float) -> float:
        return sphere + cyl / 2

    def add_power(self, a_sphere: float, a_cyl: float, a_axis: float, b_sphere: float, b_cyl: float, b_axis: float) -> Tuple[float, float, float]:
        s = a_sphere + b_sphere
        c = a_cyl + b_cyl
        if abs(a_axis - b_axis) > 90:
            c = abs(a_cyl - b_cyl)
        axis = (a_axis + b_axis) / 2 % 180
        return s, c, axis

    def vertex_distance_compensation(self, power: float, vertex_distance_mm: float = 12.0) -> float:
        d = vertex_distance_mm / 1000
        return power / (1 - d * power) if (1 - d * power) != 0 else power

    def myopia_level(self, se: float) -> str:
        if se <= -6.0: return "high"
        elif se <= -3.0: return "moderate"
        elif se < 0: return "low"
        return "none"

    def astigmatism_level(self, cyl: float) -> str:
        if abs(cyl) >= 2.5: return "high"
        elif abs(cyl) >= 1.0: return "moderate"
        elif abs(cyl) > 0: return "low"
        return "none"

    def stats(self) -> Dict:
        se_od = self.spherical_equivalent(self.sphere_od, self.cyl_od)
        se_os = self.spherical_equivalent(self.sphere_os, self.cyl_os)
        return {
            "SE_OD": round(se_od, 2),
            "SE_OS": round(se_os, 2),
            "myopia_OD": self.myopia_level(se_od),
            "myopia_OS": self.myopia_level(se_os),
            "astig_OD": self.astigmatism_level(self.cyl_od),
            "astig_OS": self.astigmatism_level(self.cyl_os)
        }

def run():
    rc = RefractionCalculator(sphere_od=-4.5, cyl_od=-1.75, axis_od=180, sphere_os=-3.0, cyl_os=-0.75, axis_os=90)
    print(rc.stats())
    print("Vertex compensated -4.5:", rc.vertex_distance_compensation(-4.5))

if __name__ == "__main__":
    run()
