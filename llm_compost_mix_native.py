"""Compost Mix Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CompostMix:
    green_material_kg: float
    brown_material_kg: float
    moisture_percent: float = 50.0
    turn_frequency_days: float = 7.0

    def carbon_to_nitrogen_ratio(self) -> float:
        if self.green_material_kg <= 0:
            return 0.0
        green_c = self.green_material_kg * 15
        brown_c = self.brown_material_kg * 40
        green_n = self.green_material_kg * 1.0
        brown_n = self.brown_material_kg * 0.5
        total_c = green_c + brown_c
        total_n = green_n + brown_n
        if total_n <= 0:
            return 0.0
        return round(total_c / total_n, 1)

    def is_balanced(self) -> bool:
        cnr = self.carbon_to_nitrogen_ratio()
        return 25 <= cnr <= 35

    def total_mass_kg(self) -> float:
        return round(self.green_material_kg + self.brown_material_kg, 2)

    def water_mass_kg(self) -> float:
        return round(self.total_mass_kg() * self.moisture_percent / 100.0, 2)

    def dry_mass_kg(self) -> float:
        return round(self.total_mass_kg() - self.water_mass_kg(), 2)

    def composting_time_weeks(self) -> float:
        cnr = self.carbon_to_nitrogen_ratio()
        if not self.is_balanced():
            return 12.0
        turn_factor = 1.0 + (self.turn_frequency_days - 7) / 14.0
        return round(8 * turn_factor, 1)

    def volume_reduction_percent(self) -> float:
        return round(50 + (self.turn_frequency_days / 7.0) * 5, 1)

    def final_compost_kg(self) -> float:
        return round(self.total_mass_kg() * (1 - self.volume_reduction_percent() / 100.0), 2)

    def stats(self) -> Dict[str, float]:
        return {
            "c_n_ratio": self.carbon_to_nitrogen_ratio(),
            "total_mass_kg": self.total_mass_kg(),
            "composting_time_weeks": self.composting_time_weeks(),
        }

    def run(self):
        print("=" * 60)
        print("COMPOST MIX CALCULATOR")
        print("=" * 60)
        comp = CompostMix(
            green_material_kg=50, brown_material_kg=100,
            moisture_percent=55, turn_frequency_days=7
        )
        print(f"Green: {comp.green_material_kg} kg, Brown: {comp.brown_material_kg} kg")
        print(f"C/N ratio: {comp.carbon_to_nitrogen_ratio():.1f}")
        print(f"Balanced: {comp.is_balanced()}")
        print(f"Total mass: {comp.total_mass_kg():.2f} kg")
        print(f"Water mass: {comp.water_mass_kg():.2f} kg")
        print(f"Composting time: {comp.composting_time_weeks():.1f} weeks")
        print(f"Volume reduction: {comp.volume_reduction_percent():.1f}%")
        print(f"Final compost: {comp.final_compost_kg():.2f} kg")
        print(f"Stats: {comp.stats()}")

if __name__ == "__main__":
    CompostMix(0, 0).run()
