"""Native stdlib module: Lens Power Calculator
Calculates lens power, focal length, and vergence for optics.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class LensPowerCalculator:
    focal_length_mm: float = 0.0
    lens_power_diopters: float = 0.0
    object_distance_m: float = 0.0
    image_distance_m: float = 0.0

    def power_from_focal_length(self) -> float:
        if self.focal_length_mm == 0:
            return 0.0
        return 1000 / self.focal_length_mm

    def focal_length_from_power(self) -> float:
        if self.lens_power_diopters == 0:
            return 0.0
        return 1000 / self.lens_power_diopters

    def lens_formula_image_distance(self) -> float:
        if self.lens_power_diopters == 0 or self.object_distance_m == 0:
            return 0.0
        return 1 / (self.lens_power_diopters - (1 / self.object_distance_m))

    def magnification(self) -> float:
        if self.object_distance_m == 0:
            return 0.0
        image_dist = self.lens_formula_image_distance()
        return image_dist / self.object_distance_m

    def near_point_power_add(self, near_point_m: float = 0.4) -> float:
        if near_point_m == 0:
            return 0.0
        return 1 / near_point_m

    def effective_power_at_vertex(self, original_power_d: float, vertex_distance_m: float) -> float:
        if vertex_distance_m == 0:
            return original_power_d
        return original_power_d / (1 - vertex_distance_m * original_power_d)

    def stats(self) -> Dict:
        return {
            "focal_length_mm": round(self.focal_length_from_power(), 1) if self.lens_power_diopters else self.focal_length_mm,
            "lens_power_diopters": round(self.power_from_focal_length(), 2) if self.focal_length_mm else self.lens_power_diopters,
            "image_distance_m": round(self.lens_formula_image_distance(), 3) if self.object_distance_m else None,
            "magnification": round(self.magnification(), 3) if self.object_distance_m else None,
            "near_point_add_d": round(self.near_point_power_add(), 2),
        }

def run():
    lp = LensPowerCalculator(lens_power_diopters=4.0, object_distance_m=0.25)
    print(lp.stats())

if __name__ == "__main__":
    run()
