"""Vulcanization Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class Vulcanization:
    rubber_mass_kg: float
    sulfur_percent: float = 2.0
    accelerator_percent: float = 0.5
    temperature_c: float = 150.0
    time_minutes: float = 15.0
    mold_thickness_mm: float = 10.0

    def heat_requirement_kj(self) -> float:
        specific_heat = 2.0
        heat = self.rubber_mass_kg * specific_heat * (self.temperature_c - 25)
        return round(heat, 2)

    def curing_rate(self) -> float:
        base_rate = 0.05
        temp_factor = math.exp((self.temperature_c - 150) / 10.0)
        rate = base_rate * temp_factor * (1 + self.accelerator_percent / 2.0)
        return round(rate, 4)

    def degree_of_cure(self) -> float:
        rate = self.curing_rate()
        cure = 1 - math.exp(-rate * self.time_minutes)
        return round(min(cure, 1.0), 4)

    def sulfur_required_kg(self) -> float:
        return round(self.rubber_mass_kg * self.sulfur_percent / 100.0, 3)

    def accelerator_required_kg(self) -> float:
        return round(self.rubber_mass_kg * self.accelerator_percent / 100.0, 3)

    def mold_heat_time_seconds(self) -> float:
        thermal_diffusivity = 0.12
        time = (self.mold_thickness_mm ** 2) / (4 * thermal_diffusivity)
        return round(time, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "heat_requirement_kj": self.heat_requirement_kj(),
            "degree_of_cure": self.degree_of_cure(),
            "curing_rate": self.curing_rate(),
        }

    def run(self):
        print("=" * 60)
        print("VULCANIZATION CALCULATOR")
        print("=" * 60)
        vulc = Vulcanization(
            rubber_mass_kg=50.0, sulfur_percent=2.5, accelerator_percent=0.8,
            temperature_c=160.0, time_minutes=20.0, mold_thickness_mm=15.0
        )
        print(f"Rubber mass: {vulc.rubber_mass_kg} kg")
        print(f"Heat required: {vulc.heat_requirement_kj():.2f} kJ")
        print(f"Sulfur required: {vulc.sulfur_required_kg():.3f} kg")
        print(f"Accelerator required: {vulc.accelerator_required_kg():.3f} kg")
        print(f"Curing rate: {vulc.curing_rate():.4f}")
        print(f"Degree of cure: {vulc.degree_of_cure():.4f}")
        print(f"Mold heat time: {vulc.mold_heat_time_seconds():.1f} s")
        print(f"Stats: {vulc.stats()}")

if __name__ == "__main__":
    Vulcanization(0).run()
