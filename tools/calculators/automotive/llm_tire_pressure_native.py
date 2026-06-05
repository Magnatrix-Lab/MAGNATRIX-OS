"""Tire Pressure Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class TirePressure:
    tire_width_mm: float
    aspect_ratio: float
    rim_diameter_inch: float
    vehicle_weight_kg: float
    axle_distribution: float = 0.5
    pressure_front_psi: float = 32.0
    pressure_rear_psi: float = 32.0

    def tire_diameter_mm(self) -> float:
        sidewall_height = self.tire_width_mm * (self.aspect_ratio / 100.0)
        rim_mm = self.rim_diameter_inch * 25.4
        return (2 * sidewall_height) + rim_mm

    def tire_volume_approx_liters(self) -> float:
        sidewall = self.tire_width_mm * (self.aspect_ratio / 100.0) / 1000.0
        radius_m = self.tire_diameter_mm() / 2000.0
        width_m = self.tire_width_mm / 1000.0
        volume = 2 * math.pi * radius_m * width_m * sidewall
        return round(volume * 1000, 2)

    def recommended_pressure_load(self) -> float:
        axle_weight = self.vehicle_weight_kg * self.axle_distribution
        recommended = axle_weight * 0.15 + 20
        return round(recommended, 1)

    def pressure_delta(self) -> Dict[str, float]:
        rec = self.recommended_pressure_load()
        return {
            "front_delta": round(self.pressure_front_psi - rec, 1),
            "rear_delta": round(self.pressure_rear_psi - rec, 1),
        }

    def load_capacity_index(self) -> float:
        total_pressure = (self.pressure_front_psi + self.pressure_rear_psi) / 2.0
        contact_patch = self.tire_width_mm / 1000.0 * 0.15
        return round(total_pressure * contact_patch * 6.89, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "tire_diameter_mm": round(self.tire_diameter_mm(), 1),
            "recommended_pressure_psi": self.recommended_pressure_load(),
            "volume_liters": self.tire_volume_approx_liters(),
        }

    def run(self):
        print("=" * 60)
        print("TIRE PRESSURE CALCULATOR")
        print("=" * 60)
        tire = TirePressure(
            tire_width_mm=225, aspect_ratio=45, rim_diameter_inch=17,
            vehicle_weight_kg=1500, axle_distribution=0.52,
            pressure_front_psi=34, pressure_rear_psi=36
        )
        print(f"Tire size: {tire.tire_width_mm}/{tire.aspect_ratio}R{tire.rim_diameter_inch}")
        print(f"Tire diameter: {tire.tire_diameter_mm():.1f} mm")
        print(f"Approx volume: {tire.tire_volume_approx_liters():.2f} L")
        print(f"Recommended pressure: {tire.recommended_pressure_load():.1f} psi")
        print(f"Pressure delta: {tire.pressure_delta()}")
        print(f"Stats: {tire.stats()}")

if __name__ == "__main__":
    TirePressure(0, 0, 0, 0).run()
