"""Pigment Concentration Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PigmentConcentration:
    pigment_weight_g: float
    total_paint_weight_g: float
    pigment_density_g_cm3: float = 4.0
    vehicle_density_g_cm3: float = 1.0

    def pigment_volume_percent(self) -> float:
        if self.total_paint_weight_g <= 0:
            return 0.0
        pigment_vol = self.pigment_weight_g / self.pigment_density_g_cm3
        vehicle_weight = self.total_paint_weight_g - self.pigment_weight_g
        vehicle_vol = vehicle_weight / self.vehicle_density_g_cm3 if vehicle_weight > 0 else 0
        total_vol = pigment_vol + vehicle_vol
        if total_vol <= 0:
            return 0.0
        return round(pigment_vol / total_vol * 100, 2)

    def weight_percent(self) -> float:
        if self.total_paint_weight_g <= 0:
            return 0.0
        return round(self.pigment_weight_g / self.total_paint_weight_g * 100, 2)

    def pigment_volume_liters(self) -> float:
        return round(self.pigment_weight_g / self.pigment_density_g_cm3 / 1000, 4)

    def color_strength_index(self) -> float:
        if self.total_paint_weight_g <= 0:
            return 0.0
        return round(self.pigment_weight_g / self.total_paint_weight_g * 1000, 2)

    def hiding_power(self, contrast_ratio: float = 0.98) -> float:
        if self.pigment_weight_g <= 0:
            return 0.0
        pvc = self.pigment_volume_percent()
        hiding = pvc * math.log(1 / (1 - contrast_ratio)) / 100.0
        return round(hiding, 3)

    def stats(self) -> Dict[str, float]:
        return {
            "pigment_volume_percent": self.pigment_volume_percent(),
            "weight_percent": self.weight_percent(),
            "color_strength_index": self.color_strength_index(),
        }

    def run(self):
        print("=" * 60)
        print("PIGMENT CONCENTRATION CALCULATOR")
        print("=" * 60)
        pig = PigmentConcentration(
            pigment_weight_g=250, total_paint_weight_g=1000,
            pigment_density_g_cm3=4.2, vehicle_density_g_cm3=0.95
        )
        print(f"Pigment: {pig.pigment_weight_g} g")
        print(f"Total paint: {pig.total_paint_weight_g} g")
        print(f"Pigment volume %: {pig.pigment_volume_percent():.2f}%")
        print(f"Weight %: {pig.weight_percent():.2f}%")
        print(f"Pigment volume: {pig.pigment_volume_liters():.4f} L")
        print(f"Color strength: {pig.color_strength_index():.2f}")
        print(f"Hiding power: {pig.hiding_power():.3f}")
        print(f"Stats: {pig.stats()}")

if __name__ == "__main__":
    PigmentConcentration(0, 0).run()
