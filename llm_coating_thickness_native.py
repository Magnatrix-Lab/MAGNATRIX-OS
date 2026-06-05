"""Coating Thickness Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CoatingThickness:
    wet_thickness_um: float
    solid_content_percent: float = 50.0
    transfer_efficiency: float = 70.0
    substrate_area_sqm: float = 10.0

    def dry_thickness_um(self) -> float:
        return round(self.wet_thickness_um * self.solid_content_percent / 100.0, 2)

    def applied_dry_thickness_um(self) -> float:
        return round(self.dry_thickness_um() * self.transfer_efficiency / 100.0, 2)

    def paint_volume_liters(self) -> float:
        if self.wet_thickness_um <= 0:
            return 0.0
        volume = self.substrate_area_sqm * self.wet_thickness_um / 1e6 * 1000
        return round(volume / (self.transfer_efficiency / 100.0), 3)

    def paint_weight_kg(self, density_kg_l: float = 1.2) -> float:
        return round(self.paint_volume_liters() * density_kg_l, 3)

    def coverage_sqm_per_liter(self) -> float:
        if self.wet_thickness_um <= 0:
            return 0.0
        return round(1.0 / (self.wet_thickness_um / 1e6 * 1000), 2)

    def stats(self) -> Dict[str, float]:
        return {
            "dry_thickness_um": self.dry_thickness_um(),
            "applied_dry_thickness_um": self.applied_dry_thickness_um(),
            "paint_volume_liters": self.paint_volume_liters(),
        }

    def run(self):
        print("=" * 60)
        print("COATING THICKNESS CALCULATOR")
        print("=" * 60)
        coat = CoatingThickness(
            wet_thickness_um=120, solid_content_percent=45.0,
            transfer_efficiency=65.0, substrate_area_sqm=50.0
        )
        print(f"Wet thickness: {coat.wet_thickness_um} um")
        print(f"Dry thickness: {coat.dry_thickness_um():.2f} um")
        print(f"Applied dry thickness: {coat.applied_dry_thickness_um():.2f} um")
        print(f"Paint volume: {coat.paint_volume_liters():.3f} L")
        print(f"Paint weight: {coat.paint_weight_kg():.3f} kg")
        print(f"Coverage: {coat.coverage_sqm_per_liter():.2f} sqm/L")
        print(f"Stats: {coat.stats()}")

if __name__ == "__main__":
    CoatingThickness(0).run()
