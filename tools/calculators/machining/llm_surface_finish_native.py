"""Surface Finish Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SurfaceFinish:
    feed_per_revolution_mm: float
    tool_nose_radius_mm: float
    cutting_speed_m_per_min: float = 200.0

    def theoretical_roughness_ra_um(self) -> float:
        if self.tool_nose_radius_mm <= 0:
            return 0.0
        return round(self.feed_per_revolution_mm ** 2 / (8 * self.tool_nose_radius_mm) * 1000, 3)

    def theoretical_roughness_rz_um(self) -> float:
        return round(self.theoretical_roughness_ra_um() * 4, 3)

    def peak_to_valley_height_um(self) -> float:
        if self.tool_nose_radius_mm <= 0:
            return 0.0
        return round(self.feed_per_revolution_mm ** 2 / (2 * self.tool_nose_radius_mm) * 1000, 3)

    def actual_roughness_ra_um(self, process_factor: float = 1.5) -> float:
        return round(self.theoretical_roughness_ra_um() * process_factor, 3)

    def required_nose_radius_for_ra(self, target_ra_um: float) -> float:
        if target_ra_um <= 0:
            return 0.0
        return round(self.feed_per_revolution_mm ** 2 * 1000 / (8 * target_ra_um), 3)

    def required_feed_for_ra(self, target_ra_um: float) -> float:
        if target_ra_um <= 0 or self.tool_nose_radius_mm <= 0:
            return 0.0
        return round(math.sqrt(8 * target_ra_um * self.tool_nose_radius_mm / 1000), 4)

    def is_surface_ok(self, required_ra_um: float = 1.6) -> bool:
        return self.actual_roughness_ra_um() <= required_ra_um

    def stats(self) -> Dict[str, float]:
        return {
            "theoretical_ra_um": self.theoretical_roughness_ra_um(),
            "actual_ra_um": self.actual_roughness_ra_um(),
            "peak_to_valley_um": self.peak_to_valley_height_um(),
        }

    def run(self):
        print("=" * 60)
        print("SURFACE FINISH CALCULATOR")
        print("=" * 60)
        sf = SurfaceFinish(
            feed_per_revolution_mm=0.2, tool_nose_radius_mm=0.8, cutting_speed_m_per_min=250
        )
        print(f"Feed: {sf.feed_per_revolution_mm} mm/rev")
        print(f"Nose radius: {sf.tool_nose_radius_mm} mm")
        print(f"Theoretical Ra: {sf.theoretical_roughness_ra_um():.3f} um")
        print(f"Actual Ra: {sf.actual_roughness_ra_um():.3f} um")
        print(f"Rz: {sf.theoretical_roughness_rz_um():.3f} um")
        print(f"Peak-valley: {sf.peak_to_valley_height_um():.3f} um")
        print(f"OK for 1.6um: {sf.is_surface_ok(1.6)}")
        print(f"Stats: {sf.stats()}")

if __name__ == "__main__":
    SurfaceFinish(0, 0).run()
