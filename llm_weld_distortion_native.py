"""Weld Distortion Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class WeldDistortion:
    plate_thickness_mm: float
    weld_length_m: float
    heat_input_kj_per_mm: float
    material: str = "steel"
    restraint_condition: str = "free"

    def thermal_expansion_coefficient(self) -> float:
        coeffs = {"steel": 1.2e-5, "aluminum": 2.3e-5, "stainless": 1.8e-5, "titanium": 8.6e-6}
        return coeffs.get(self.material, 1.2e-5)

    def angular_distortion_rad(self) -> float:
        alpha = self.thermal_expansion_coefficient()
        hi = self.heat_input_kj_per_mm()
        restraints = {"free": 1.0, "partial": 0.6, "fixed": 0.3}
        r = restraints.get(self.restraint_condition, 1.0)
        return round(alpha * hi * 1000 / self.plate_thickness_mm * r, 6)

    def angular_distortion_deg(self) -> float:
        return round(self.angular_distortion_rad() * 180 / math.pi, 3)

    def longitudinal_shrinkage_mm(self) -> float:
        return round(self.weld_length_m * 1000 * self.thermal_expansion_coefficient() * self.heat_input_kj_per_mm() / 10, 2)

    def transverse_shrinkage_mm(self) -> float:
        return round(self.plate_thickness_mm * 0.05 * self.heat_input_kj_per_mm(), 2)

    def distortion_control_factor(self) -> float:
        return round(1.0 / (1 + self.weld_length_m / 2), 3)

    def stats(self) -> Dict[str, float]:
        return {
            "angular_distortion_deg": self.angular_distortion_deg(),
            "longitudinal_shrinkage_mm": self.longitudinal_shrinkage_mm(),
            "transverse_shrinkage_mm": self.transverse_shrinkage_mm(),
        }

    def run(self):
        print("=" * 60)
        print("WELD DISTORTION CALCULATOR")
        print("=" * 60)
        wd = WeldDistortion(
            plate_thickness_mm=10, weld_length_m=2.0,
            heat_input_kj_per_mm=1.0, material="steel", restraint_condition="partial"
        )
        print(f"Plate: {wd.plate_thickness_mm} mm, Length: {wd.weld_length_m} m")
        print(f"Angular: {wd.angular_distortion_deg():.3f} deg")
        print(f"Longitudinal: {wd.longitudinal_shrinkage_mm():.2f} mm")
        print(f"Transverse: {wd.transverse_shrinkage_mm():.2f} mm")
        print(f"Control factor: {wd.distortion_control_factor():.3f}")
        print(f"Stats: {wd.stats()}")

if __name__ == "__main__":
    WeldDistortion(0, 0, 0).run()
