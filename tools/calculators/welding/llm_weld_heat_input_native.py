"""Weld Heat Input Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class WeldHeatInput:
    voltage_v: float
    current_a: float
    travel_speed_mm_per_min: float
    process_efficiency: float = 0.85

    def heat_input_kj_per_mm(self) -> float:
        if self.travel_speed_mm_per_min <= 0:
            return 0.0
        return round(self.voltage_v * self.current_a * 60 / self.travel_speed_mm_per_min * self.process_efficiency / 1000, 3)

    def heat_input_kj_per_cm(self) -> float:
        return round(self.heat_input_kj_per_mm() * 10, 3)

    def heat_input_j_per_mm(self) -> float:
        return round(self.heat_input_kj_per_mm() * 1000, 2)

    def power_kw(self) -> float:
        return round(self.voltage_v * self.current_a / 1000, 2)

    def recommended_heat_input(self, material_thickness_mm: float) -> float:
        if material_thickness_mm <= 3:
            return 0.5
        elif material_thickness_mm <= 10:
            return 1.0
        else:
            return 1.5

    def is_heat_input_ok(self, material_thickness_mm: float) -> bool:
        actual = self.heat_input_kj_per_mm()
        recommended = self.recommended_heat_input(material_thickness_mm)
        return actual <= recommended * 1.5

    def cooling_rate_c_per_s(self, material_thickness_mm: float = 10.0) -> float:
        hi = self.heat_input_kj_per_mm()
        if hi <= 0:
            return 0.0
        return round(100 / (hi * material_thickness_mm), 2)

    def stats(self) -> Dict[str, float]:
        return {
            "heat_input_kj_per_mm": self.heat_input_kj_per_mm(),
            "power_kw": self.power_kw(),
            "cooling_rate": self.cooling_rate_c_per_s(),
        }

    def run(self):
        print("=" * 60)
        print("WELD HEAT INPUT CALCULATOR")
        print("=" * 60)
        whi = WeldHeatInput(
            voltage_v=28, current_a=250, travel_speed_mm_per_min=400, process_efficiency=0.85
        )
        print(f"V: {whi.voltage_v} V, A: {whi.current_a} A")
        print(f"Speed: {whi.travel_speed_mm_per_min} mm/min")
        print(f"Heat input: {whi.heat_input_kj_per_mm():.3f} kJ/mm")
        print(f"Power: {whi.power_kw():.2f} kW")
        print(f"Cooling rate: {whi.cooling_rate_c_per_s():.2f} C/s")
        print(f"OK for 10mm: {whi.is_heat_input_ok(10)}")
        print(f"Stats: {whi.stats()}")

if __name__ == "__main__":
    WeldHeatInput(0, 0, 0).run()
