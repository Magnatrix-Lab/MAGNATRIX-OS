"""Weld Deposition Rate Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class WeldDepositionRate:
    wire_diameter_mm: float
    wire_feed_speed_m_per_min: float
    process_type: str = "mig"
    electrode_density_g_cm3: float = 7.8

    def wire_cross_section_mm2(self) -> float:
        return round(math.pi * (self.wire_diameter_mm / 2) ** 2, 2)

    def wire_volume_mm3_per_min(self) -> float:
        return round(self.wire_cross_section_mm2() * self.wire_feed_speed_m_per_min * 1000, 1)

    def deposition_rate_kg_per_h(self) -> float:
        volume = self.wire_volume_mm3_per_min()
        mass_g = volume * self.electrode_density_g_cm3 / 1000.0
        efficiency = {"mig": 0.95, "tig": 0.85, "flux_core": 0.90, "submerged": 0.98, "stick": 0.80}
        eff = efficiency.get(self.process_type, 0.9)
        return round(mass_g * 60 * eff / 1000, 2)

    def deposition_rate_kg_per_hr_alternate(self) -> float:
        if self.wire_diameter_mm <= 0:
            return 0.0
        k = 0.0016
        return round(k * self.wire_diameter_mm ** 2 * self.wire_feed_speed_m_per_min, 2)

    def weld_bead_area_mm2(self, travel_speed_mm_per_min: float = 300.0) -> float:
        if travel_speed_mm_per_min <= 0:
            return 0.0
        dep_rate = self.deposition_rate_kg_per_h()
        return round(dep_rate * 1000 * 1000 / (travel_speed_mm_per_min * 60 * self.electrode_density_g_cm3), 2)

    def arc_time_percent(self, total_cycle_time_min: float = 10.0) -> float:
        if total_cycle_time_min <= 0:
            return 0.0
        arc_time = 1.0
        return round(arc_time / total_cycle_time_min * 100, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "deposition_rate_kg_per_h": self.deposition_rate_kg_per_h(),
            "wire_cross_section_mm2": self.wire_cross_section_mm2(),
        }

    def run(self):
        print("=" * 60)
        print("WELD DEPOSITION RATE CALCULATOR")
        print("=" * 60)
        wdr = WeldDepositionRate(
            wire_diameter_mm=1.2, wire_feed_speed_m_per_min=8.0, process_type="mig"
        )
        print(f"Wire: {wdr.wire_diameter_mm} mm @ {wdr.wire_feed_speed_m_per_min} m/min")
        print(f"Process: {wdr.process_type}")
        print(f"Cross-section: {wdr.wire_cross_section_mm2():.2f} mm2")
        print(f"Deposition rate: {wdr.deposition_rate_kg_per_h():.2f} kg/h")
        print(f"Bead area (300mm/min): {wdr.weld_bead_area_mm2():.2f} mm2")
        print(f"Stats: {wdr.stats()}")

if __name__ == "__main__":
    WeldDepositionRate(0, 0).run()
