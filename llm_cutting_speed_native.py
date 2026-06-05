"""Cutting Speed Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CuttingSpeed:
    tool_diameter_mm: float
    spindle_speed_rpm: float
    material: str = "steel"
    operation: str = "turning"

    def cutting_speed_m_per_min(self) -> float:
        return round(math.pi * self.tool_diameter_mm * self.spindle_speed_rpm / 1000.0, 1)

    def cutting_speed_m_per_s(self) -> float:
        return round(self.cutting_speed_m_per_min() / 60.0, 3)

    def recommended_speed_m_per_min(self) -> float:
        speeds = {
            "steel": {"turning": 200, "milling": 150, "drilling": 30, "grinding": 25},
            "aluminum": {"turning": 400, "milling": 300, "drilling": 60, "grinding": 20},
            "stainless": {"turning": 100, "milling": 80, "drilling": 20, "grinding": 20},
        }
        return speeds.get(self.material, {}).get(self.operation, 150)

    def speed_factor(self) -> float:
        rec = self.recommended_speed_m_per_min()
        if rec <= 0:
            return 0.0
        return round(self.cutting_speed_m_per_min() / rec, 2)

    def spindle_speed_for_recommended_rpm(self) -> float:
        rec = self.recommended_speed_m_per_min()
        if self.tool_diameter_mm <= 0:
            return 0.0
        return round(rec * 1000.0 / (math.pi * self.tool_diameter_mm), 1)

    def feed_rate_mm_per_min(self, feed_per_revolution_mm: float = 0.2) -> float:
        return round(self.spindle_speed_rpm * feed_per_revolution_mm, 1)

    def material_removal_rate_cm3_per_min(self, depth_of_cut_mm: float = 2.0,
                                         width_of_cut_mm: float = 2.0) -> float:
        feed = self.feed_rate_mm_per_min()
        return round(feed * depth_of_cut_mm * width_of_cut_mm / 1000.0, 3)

    def stats(self) -> Dict[str, float]:
        return {
            "cutting_speed_m_per_min": self.cutting_speed_m_per_min(),
            "recommended_speed": self.recommended_speed_m_per_min(),
            "spindle_speed_for_recommended": self.spindle_speed_for_recommended_rpm(),
        }

    def run(self):
        print("=" * 60)
        print("CUTTING SPEED CALCULATOR")
        print("=" * 60)
        cs = CuttingSpeed(
            tool_diameter_mm=12, spindle_speed_rpm=2000, material="steel", operation="turning"
        )
        print(f"Tool: {cs.tool_diameter_mm} mm @ {cs.spindle_speed_rpm} RPM")
        print(f"Cutting speed: {cs.cutting_speed_m_per_min():.1f} m/min")
        print(f"Recommended: {cs.recommended_speed_m_per_min():.1f} m/min")
        print(f"Speed factor: {cs.speed_factor():.2f}")
        print(f"RPM for rec: {cs.spindle_speed_for_recommended_rpm():.1f}")
        print(f"Feed rate: {cs.feed_rate_mm_per_min():.1f} mm/min")
        print(f"MRR: {cs.material_removal_rate_cm3_per_min():.3f} cm3/min")
        print(f"Stats: {cs.stats()}")

if __name__ == "__main__":
    CuttingSpeed(0, 0).run()
