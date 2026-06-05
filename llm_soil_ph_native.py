"""Soil pH Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SoilPH:
    current_ph: float
    target_ph: float
    soil_weight_kg: float
    soil_type: str = "loam"
    cec_meq_per_100g: float = 15.0

    def ph_change_required(self) -> float:
        return round(self.target_ph - self.current_ph, 2)

    def lime_required_kg(self) -> float:
        delta = abs(self.ph_change_required())
        if delta <= 0:
            return 0.0
        factors = {"sand": 0.5, "loam": 1.0, "clay": 2.0, "silt": 1.2}
        factor = factors.get(self.soil_type, 1.0)
        return round(self.soil_weight_kg * delta * factor * 0.05, 2)

    def sulfur_required_kg(self) -> float:
        delta = abs(self.ph_change_required())
        if delta <= 0 or self.target_ph >= self.current_ph:
            return 0.0
        return round(self.soil_weight_kg * delta * 0.02, 2)

    def is_acidic(self) -> bool:
        return self.current_ph < 6.5

    def is_alkaline(self) -> bool:
        return self.current_ph > 7.5

    def buffer_capacity(self) -> float:
        return round(self.cec_meq_per_100g / 10.0, 2)

    def nutrient_availability(self, nutrient: str) -> float:
        availabilities = {
            "nitrogen": max(0, 100 - abs(self.current_ph - 6.5) * 20),
            "phosphorus": max(0, 100 - abs(self.current_ph - 6.5) * 25),
            "potassium": max(0, 100 - abs(self.current_ph - 6.0) * 10),
            "iron": max(0, 100 - (self.current_ph - 5.0) * 15) if self.current_ph > 5 else 100,
        }
        return round(availabilities.get(nutrient, 80), 2)

    def stats(self) -> Dict[str, float]:
        return {
            "ph_change_required": self.ph_change_required(),
            "lime_required_kg": self.lime_required_kg(),
            "buffer_capacity": self.buffer_capacity(),
        }

    def run(self):
        print("=" * 60)
        print("SOIL pH CALCULATOR")
        print("=" * 60)
        soil = SoilPH(
            current_ph=5.5, target_ph=6.5, soil_weight_kg=1000,
            soil_type="clay", cec_meq_per_100g=20
        )
        print(f"Current pH: {soil.current_ph}")
        print(f"Target pH: {soil.target_ph}")
        print(f"Change needed: {soil.ph_change_required():.2f}")
        print(f"Lime required: {soil.lime_required_kg():.2f} kg")
        print(f"Sulfur required: {soil.sulfur_required_kg():.2f} kg")
        print(f"Acidic: {soil.is_acidic()}, Alkaline: {soil.is_alkaline()}")
        print(f"Buffer capacity: {soil.buffer_capacity():.2f}")
        print(f"N availability: {soil.nutrient_availability('nitrogen'):.2f}%")
        print(f"Stats: {soil.stats()}")

if __name__ == "__main__":
    SoilPH(0, 0, 0).run()
