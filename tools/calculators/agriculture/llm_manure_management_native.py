"""Manure Management Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ManureManagement:
    animal_count: int
    animal_type: str
    days: int = 365
    bedding_kg_per_animal_per_day: float = 2.0

    def manure_per_animal_kg_per_day(self) -> float:
        rates = {"dairy_cow": 50, "beef_cattle": 35, "pig": 8, "sheep": 5, "goat": 4, "chicken": 0.15}
        return rates.get(self.animal_type, 20)

    def total_manure_kg(self) -> float:
        return round(self.animal_count * self.manure_per_animal_kg_per_day() * self.days, 1)

    def total_bedding_kg(self) -> float:
        return round(self.animal_count * self.bedding_kg_per_animal_per_day * self.days, 1)

    def total_waste_kg(self) -> float:
        return round(self.total_manure_kg() + self.total_bedding_kg(), 1)

    def nitrogen_content_kg(self) -> float:
        return round(self.total_manure_kg() * 0.005, 1)

    def phosphorus_content_kg(self) -> float:
        return round(self.total_manure_kg() * 0.001, 1)

    def potassium_content_kg(self) -> float:
        return round(self.total_manure_kg() * 0.003, 1)

    def biogas_potential_m3(self) -> float:
        return round(self.total_manure_kg() * 0.02, 1)

    def compost_output_kg(self) -> float:
        return round(self.total_waste_kg() * 0.4, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "total_manure_kg": self.total_manure_kg(),
            "total_waste_kg": self.total_waste_kg(),
            "nitrogen_kg": self.nitrogen_content_kg(),
        }

    def run(self):
        print("=" * 60)
        print("MANURE MANAGEMENT CALCULATOR")
        print("=" * 60)
        mm = ManureManagement(
            animal_count=100, animal_type="dairy_cow", days=365, bedding_kg_per_animal_per_day=3
        )
        print(f"Animals: {mm.animal_count} {mm.animal_type}")
        print(f"Manure/animal/day: {mm.manure_per_animal_kg_per_day()} kg")
        print(f"Total manure: {mm.total_manure_kg():.1f} kg")
        print(f"Total bedding: {mm.total_bedding_kg():.1f} kg")
        print(f"Total waste: {mm.total_waste_kg():.1f} kg")
        print(f"N: {mm.nitrogen_content_kg():.1f} kg, P: {mm.phosphorus_content_kg():.1f} kg, K: {mm.potassium_content_kg():.1f} kg")
        print(f"Biogas: {mm.biogas_potential_m3():.1f} m3")
        print(f"Compost: {mm.compost_output_kg():.1f} kg")
        print(f"Stats: {mm.stats()}")

if __name__ == "__main__":
    ManureManagement(0, "cattle").run()
