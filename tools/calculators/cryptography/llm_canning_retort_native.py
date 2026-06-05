"""Canning Retort Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CanningRetort:
    can_volume_liters: float
    initial_temp_c: float
    retort_temp_c: float = 121.0
    product_thermal_diffusivity_m2_s: float = 1.5e-7
    target_f0: float = 5.0

    def come_up_time_min(self) -> float:
        return round((self.retort_temp_c - self.initial_temp_c) / 5.0, 1)

    def heating_time_min(self) -> float:
        radius = (self.can_volume_liters * 1e-3 / math.pi) ** (1/3)
        if radius <= 0 or self.product_thermal_diffusivity_m2_s <= 0:
            return 0.0
        time = 0.5 * (radius ** 2) / self.product_thermal_diffusivity_m2_s / 60.0
        return round(time, 1)

    def process_time_min(self) -> float:
        return round(self.come_up_time_min() + self.heating_time_min() + 5, 1)

    def actual_f0(self, holding_time_min: float = 10.0) -> float:
        z = 10.0
        ref = 121.0
        if self.retort_temp_c <= ref:
            return 0.0
        return round(holding_time_min * math.exp((self.retort_temp_c - ref) / z), 2)

    def is_adequate(self, holding_time_min: float = 10.0) -> bool:
        return self.actual_f0(holding_time_min) >= self.target_f0

    def steam_consumption_kg(self) -> float:
        can_mass = self.can_volume_liters * 1.0
        return round(can_mass * 0.5, 3)

    def cooling_water_liters(self) -> float:
        return round(self.can_volume_liters * 5, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "come_up_time_min": self.come_up_time_min(),
            "heating_time_min": self.heating_time_min(),
            "process_time_min": self.process_time_min(),
        }

    def run(self):
        print("=" * 60)
        print("CANNING RETORT CALCULATOR")
        print("=" * 60)
        retort = CanningRetort(
            can_volume_liters=0.5, initial_temp_c=25,
            retort_temp_c=121, target_f0=5.0
        )
        print(f"Can volume: {retort.can_volume_liters} L")
        print(f"Retort temp: {retort.retort_temp_c} C")
        print(f"Come-up time: {retort.come_up_time_min():.1f} min")
        print(f"Heating time: {retort.heating_time_min():.1f} min")
        print(f"Process time: {retort.process_time_min():.1f} min")
        print(f"F0 (10 min hold): {retort.actual_f0(10):.2f}")
        print(f"Adequate: {retort.is_adequate(10)}")
        print(f"Steam: {retort.steam_consumption_kg():.3f} kg")
        print(f"Cooling water: {retort.cooling_water_liters():.1f} L")
        print(f"Stats: {retort.stats()}")

if __name__ == "__main__":
    CanningRetort(0, 0).run()
