"""Paint Spray Coverage Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PaintSprayCoverage:
    nozzle_size_mm: float
    spray_pressure_bar: float = 2.0
    paint_flow_rate_ml_min: float = 500.0
    paint_efficiency_percent: float = 65.0
    overlap_percent: float = 30.0

    def spray_width_cm(self) -> float:
        return round(self.nozzle_size_mm * 10 * (1 + self.spray_pressure_bar * 0.1), 1)

    def coverage_rate_sqm_per_min(self) -> float:
        width_m = self.spray_width_cm() / 100.0
        speed = 0.3
        overlap_factor = 1 - self.overlap_percent / 100.0
        return round(width_m * speed * 60 * overlap_factor, 2)

    def paint_consumption_ml_per_sqm(self) -> float:
        if self.coverage_rate_sqm_per_min() <= 0:
            return 0.0
        return round(self.paint_flow_rate_ml_min / self.coverage_rate_sqm_per_min(), 2)

    def effective_coverage_sqm(self, paint_volume_liters: float) -> float:
        volume_ml = paint_volume_liters * 1000
        if self.paint_consumption_ml_per_sqm() <= 0:
            return 0.0
        return round(volume_ml / self.paint_consumption_ml_per_sqm() * (self.paint_efficiency_percent / 100.0), 1)

    def transfer_efficiency_index(self) -> float:
        return round(self.paint_efficiency_percent * (1 - self.overlap_percent / 200.0), 2)

    def stats(self) -> Dict[str, float]:
        return {
            "spray_width_cm": self.spray_width_cm(),
            "coverage_rate_sqm_per_min": self.coverage_rate_sqm_per_min(),
            "paint_consumption_ml_per_sqm": self.paint_consumption_ml_per_sqm(),
        }

    def run(self):
        print("=" * 60)
        print("PAINT SPRAY COVERAGE CALCULATOR")
        print("=" * 60)
        spray = PaintSprayCoverage(
            nozzle_size_mm=1.4, spray_pressure_bar=2.5,
            paint_flow_rate_ml_min=600, paint_efficiency_percent=70, overlap_percent=25
        )
        print(f"Nozzle: {spray.nozzle_size_mm} mm")
        print(f"Pressure: {spray.spray_pressure_bar} bar")
        print(f"Spray width: {spray.spray_width_cm():.1f} cm")
        print(f"Coverage rate: {spray.coverage_rate_sqm_per_min():.2f} sqm/min")
        print(f"Consumption: {spray.paint_consumption_ml_per_sqm():.2f} ml/sqm")
        print(f"Effective coverage (5L): {spray.effective_coverage_sqm(5.0):.1f} sqm")
        print(f"Transfer efficiency: {spray.transfer_efficiency_index():.2f}")
        print(f"Stats: {spray.stats()}")

if __name__ == "__main__":
    PaintSprayCoverage(0).run()
