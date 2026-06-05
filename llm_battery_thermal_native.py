"""Battery Thermal Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class BatteryThermal:
    internal_resistance_mohm: float
    current_a: float
    ambient_temp_c: float
    thermal_resistance_kw: float = 0.05

    def heat_generation_w(self) -> float:
        r = self.internal_resistance_mohm / 1000.0
        return round(self.current_a ** 2 * r, 3)

    def temperature_rise_c(self) -> float:
        heat = self.heat_generation_w()
        return round(heat * self.thermal_resistance_kw, 2)

    def cell_temperature_c(self) -> float:
        return round(self.ambient_temp_c + self.temperature_rise_c(), 2)

    def is_thermal_runaway(self, threshold_c: float = 80.0) -> bool:
        return self.cell_temperature_c() > threshold_c

    def cooling_required_w(self, target_temp_c: float) -> float:
        if self.cell_temperature_c() <= target_temp_c:
            return 0.0
        delta = self.cell_temperature_c() - target_temp_c
        return round(delta / self.thermal_resistance_kw, 2)

    def heat_capacity_kj(self, mass_kg: float = 0.1) -> float:
        specific_heat = 1.0
        return round(mass_kg * specific_heat, 3)

    def time_to_threshold_seconds(self, threshold_c: float = 60.0) -> float:
        if self.temperature_rise_c() <= 0:
            return float('inf')
        delta = threshold_c - self.ambient_temp_c
        if delta <= 0:
            return 0.0
        return round(delta / self.temperature_rise_c() * 60, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "heat_generation_w": self.heat_generation_w(),
            "temperature_rise_c": self.temperature_rise_c(),
            "cell_temperature_c": self.cell_temperature_c(),
        }

    def run(self):
        print("=" * 60)
        print("BATTERY THERMAL CALCULATOR")
        print("=" * 60)
        th = BatteryThermal(
            internal_resistance_mohm=25, current_a=10.0, ambient_temp_c=30
        )
        print(f"IR: {th.internal_resistance_mohm} mOhm")
        print(f"Current: {th.current_a} A")
        print(f"Heat generation: {th.heat_generation_w():.3f} W")
        print(f"Temperature rise: {th.temperature_rise_c():.2f} C")
        print(f"Cell temperature: {th.cell_temperature_c():.2f} C")
        print(f"Thermal runaway: {th.is_thermal_runaway()}")
        print(f"Cooling required: {th.cooling_required_w(40):.2f} W")
        print(f"Time to 60C: {th.time_to_threshold_seconds(60):.1f} s")
        print(f"Stats: {th.stats()}")

if __name__ == "__main__":
    BatteryThermal(0, 0, 0).run()
