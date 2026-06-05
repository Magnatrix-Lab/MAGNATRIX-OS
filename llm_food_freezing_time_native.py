"""Food Freezing Time Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FoodFreezingTime:
    product_thickness_mm: float
    initial_temp_c: float
    freezing_temp_c: float = -18.0
    freezer_temp_c: float = -30.0
    thermal_conductivity_w_per_m_k: float = 1.5
    density_kg_m3: float = 1000.0
    latent_heat_kj_per_kg: float = 335.0

    def freezing_time_hours(self) -> float:
        thickness_m = self.product_thickness_mm / 1000.0
        delta_t = self.initial_temp_c - self.freezing_temp_c
        freezer_delta = self.freezing_temp_c - self.freezer_temp_c
        if freezer_delta <= 0:
            return 0.0
        h = 50.0
        p = 0.5
        r = 0.125
        time = (self.latent_heat_kj_per_kg * self.density_kg_m3 / (self.freezing_temp_c - self.freezer_temp_c)) *                (p * thickness_m / h + r * thickness_m ** 2 / self.thermal_conductivity_w_per_m_k)
        return round(time / 3600, 2)

    def surface_freezing_time_hours(self) -> float:
        return round(self.freezing_time_hours() * 0.3, 2)

    def center_freezing_time_hours(self) -> float:
        return round(self.freezing_time_hours() * 1.5, 2)

    def freezing_rate_cm_per_h(self) -> float:
        if self.freezing_time_hours() <= 0:
            return 0.0
        return round(self.product_thickness_mm / 20 / self.freezing_time_hours(), 3)

    def quality_index(self) -> float:
        rate = self.freezing_rate_cm_per_h()
        if rate <= 0:
            return 0.0
        return round(min(100, rate * 50), 2)

    def stats(self) -> Dict[str, float]:
        return {
            "freezing_time_hours": self.freezing_time_hours(),
            "surface_freezing_hours": self.surface_freezing_time_hours(),
            "center_freezing_hours": self.center_freezing_time_hours(),
        }

    def run(self):
        print("=" * 60)
        print("FOOD FREEZING TIME CALCULATOR")
        print("=" * 60)
        freeze = FoodFreezingTime(
            product_thickness_mm=50, initial_temp_c=10,
            freezer_temp_c=-35, thermal_conductivity_w_per_m_k=1.8
        )
        print(f"Thickness: {freeze.product_thickness_mm} mm")
        print(f"Initial temp: {freeze.initial_temp_c} C")
        print(f"Freezing time: {freeze.freezing_time_hours():.2f} h")
        print(f"Surface freezing: {freeze.surface_freezing_time_hours():.2f} h")
        print(f"Center freezing: {freeze.center_freezing_time_hours():.2f} h")
        print(f"Freezing rate: {freeze.freezing_rate_cm_per_h():.3f} cm/h")
        print(f"Quality index: {freeze.quality_index():.2f}")
        print(f"Stats: {freeze.stats()}")

if __name__ == "__main__":
    FoodFreezingTime(0, 0).run()
