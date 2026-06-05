"""Laser Power Density Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class LaserPowerDensity:
    laser_power_w: float
    beam_diameter_um: float
    scan_speed_mm_per_s: float = 1000.0
    hatch_spacing_um: float = 100.0

    def beam_area_um2(self) -> float:
        return round(math.pi * (self.beam_diameter_um / 2) ** 2, 2)

    def power_density_w_per_m2(self) -> float:
        area_m2 = self.beam_area_um2() * 1e-12
        if area_m2 <= 0:
            return 0.0
        return round(self.laser_power_w / area_m2, 2)

    def power_density_mw_per_cm2(self) -> float:
        return round(self.power_density_w_per_m2() / 10000, 2)

    def energy_density_j_per_m2(self) -> float:
        if self.scan_speed_mm_per_s <= 0:
            return 0.0
        dwell = self.beam_diameter_um / (self.scan_speed_mm_per_s * 1000)
        return round(self.power_density_w_per_m2() * dwell, 2)

    def volumetric_energy_density_j_per_m3(self, layer_thickness_um: float = 50.0) -> float:
        if self.hatch_spacing_um <= 0 or layer_thickness_um <= 0:
            return 0.0
        volume = self.beam_area_um2() * self.hatch_spacing_um * layer_thickness_um * 1e-18
        if volume <= 0:
            return 0.0
        return round(self.laser_power_w * (self.beam_diameter_um / (self.scan_speed_mm_per_s * 1000)) / volume, 2)

    def line_energy_j_per_m(self) -> float:
        if self.scan_speed_mm_per_s <= 0:
            return 0.0
        return round(self.laser_power_w / (self.scan_speed_mm_per_s / 1000), 2)

    def is_power_sufficient(self, material: str = "steel") -> bool:
        thresholds = {"steel": 1e9, "aluminum": 5e8, "titanium": 8e8, "copper": 1.5e9}
        return self.power_density_w_per_m2() >= thresholds.get(material, 1e9)

    def stats(self) -> Dict[str, float]:
        return {
            "power_density_w_per_m2": self.power_density_w_per_m2(),
            "energy_density_j_per_m2": self.energy_density_j_per_m2(),
            "line_energy_j_per_m": self.line_energy_j_per_m(),
        }

    def run(self):
        print("=" * 60)
        print("LASER POWER DENSITY CALCULATOR")
        print("=" * 60)
        lp = LaserPowerDensity(
            laser_power_w=200, beam_diameter_um=100, scan_speed_mm_per_s=800, hatch_spacing_um=120
        )
        print(f"Power: {lp.laser_power_w} W")
        print(f"Beam: {lp.beam_diameter_um} um")
        print(f"Power density: {lp.power_density_w_per_m2():.2e} W/m2")
        print(f"Energy density: {lp.energy_density_j_per_m2():.2e} J/m2")
        print(f"Line energy: {lp.line_energy_j_per_m():.2f} J/m")
        print(f"Sufficient for steel: {lp.is_power_sufficient('steel')}")
        print(f"Stats: {lp.stats()}")

if __name__ == "__main__":
    LaserPowerDensity(0, 0).run()
