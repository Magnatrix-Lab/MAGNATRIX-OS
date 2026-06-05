"""Native stdlib module: Refractive Calculator
Calculates sphere, cylinder, axis combinations and vertex distance conversions.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class RefractiveCalculator:
    sphere_diopters: float
    cylinder_diopters: float
    axis_degrees: float
    vertex_distance_mm: float = 12.0

    def spherical_equivalent(self) -> float:
        return self.sphere_diopters + (self.cylinder_diopters / 2)

    def vertex_compensated_sphere(self) -> float:
        d = self.vertex_distance_mm / 1000
        s = self.sphere_diopters
        if d * s == 1:
            return s
        return s / (1 - d * s)

    def vertex_compensated_cylinder(self) -> float:
        d = self.vertex_distance_mm / 1000
        s = self.sphere_diopters
        c = self.cylinder_diopters
        if d * (s + c) == 1 or d * s == 1:
            return c
        return (s + c) / (1 - d * (s + c)) - self.vertex_compensated_sphere()

    def plus_cylinder_form(self) -> Dict:
        if self.cylinder_diopters < 0:
            new_sphere = self.sphere_diopters + self.cylinder_diopters
            new_cyl = -self.cylinder_diopters
            new_axis = (self.axis_degrees + 90) % 180
            return {"sphere": round(new_sphere, 2), "cylinder": round(new_cyl, 2), "axis": new_axis}
        return {"sphere": self.sphere_diopters, "cylinder": self.cylinder_diopters, "axis": self.axis_degrees}

    def astigmatism_type(self) -> str:
        if abs(self.cylinder_diopters) < 0.5:
            return "none"
        elif self.sphere_diopters == 0:
            return "simple"
        elif self.sphere_diopters * self.cylinder_diopters > 0:
            return "compound"
        return "mixed"

    def stats(self) -> Dict:
        return {
            "sphere": self.sphere_diopters,
            "cylinder": self.cylinder_diopters,
            "axis": self.axis_degrees,
            "spherical_equivalent": round(self.spherical_equivalent(), 2),
            "vertex_compensated_sphere": round(self.vertex_compensated_sphere(), 2),
            "astigmatism_type": self.astigmatism_type(),
            "plus_cylinder_form": self.plus_cylinder_form(),
        }

def run():
    rc = RefractiveCalculator(sphere_diopters=-2.50, cylinder_diopters=-1.25, axis_degrees=90, vertex_distance_mm=12)
    print(rc.stats())

if __name__ == "__main__":
    run()
