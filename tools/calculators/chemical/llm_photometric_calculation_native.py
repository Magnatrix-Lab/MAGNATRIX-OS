"""Photometric Calculation — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PhotometricCalculation:
    luminous_intensity_cd: float
    distance_m: float
    angle_deg: float = 0.0

    def illuminance_lux(self) -> float:
        if self.distance_m <= 0:
            return 0.0
        angle_rad = math.radians(self.angle_deg)
        return round(self.luminous_intensity_cd * math.cos(angle_rad) / self.distance_m ** 2, 2)

    def luminance_cd_m2(self, projected_area_m2: float = 1.0) -> float:
        if projected_area_m2 <= 0:
            return 0.0
        return round(self.luminous_intensity_cd / projected_area_m2, 2)

    def inverse_square_distance_m(self, target_lux: float = 500.0) -> float:
        if target_lux <= 0:
            return 0.0
        return round(math.sqrt(self.luminous_intensity_cd / target_lux), 2)

    def cosine_law_illuminance(self, horizontal_lux: float = 500.0) -> float:
        angle_rad = math.radians(self.angle_deg)
        return round(horizontal_lux * math.cos(angle_rad), 2)

    def solid_angle_sr(self, area_m2: float = 1.0) -> float:
        if self.distance_m <= 0:
            return 0.0
        return round(area_m2 / self.distance_m ** 2, 6)

    def luminous_flux_lm(self, solid_angle_sr: float = 1.0) -> float:
        return round(self.luminous_intensity_cd * solid_angle_sr, 2)

    def stats(self) -> Dict[str, float]:
        return {"illuminance_lux": self.illuminance_lux(), "luminance_cd_m2": self.luminance_cd_m2(), "inverse_square_distance_m": self.inverse_square_distance_m()}

    def run(self):
        print("=" * 60)
        print("PHOTOMETRIC CALCULATION")
        print("=" * 60)
        pc = PhotometricCalculation(luminous_intensity_cd=1000, distance_m=3, angle_deg=30)
        print(f"Intensity: {pc.luminous_intensity_cd} cd @ {pc.distance_m} m")
        print(f"Illuminance: {pc.illuminance_lux():.2f} lux")
        print(f"Luminance: {pc.luminance_cd_m2():.2f} cd/m2")
        print(f"Distance for 500 lux: {pc.inverse_square_distance_m():.2f} m")
        print(f"Solid angle (1m2): {pc.solid_angle_sr():.6f} sr")
        print(f"Stats: {pc.stats()}")

if __name__ == "__main__":
    PhotometricCalculation(0, 0).run()
