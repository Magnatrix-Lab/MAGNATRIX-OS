"""SLA Resin Exposure Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SLAResinExposure:
    layer_thickness_mm: float
    resin_type: str = "standard"
    printer_uv_power_mw: float = 5.0

    def base_exposure_time_s(self) -> float:
        times = {"standard": 6, "tough": 8, "flexible": 10, "castable": 12, "dental": 4}
        return times.get(self.resin_type, 6)

    def exposure_time_s(self) -> float:
        return round(self.base_exposure_time_s() * (self.layer_thickness_mm / 0.05), 2)

    def bottom_layer_exposure_s(self) -> float:
        return round(self.exposure_time_s() * 8, 1)

    def bottom_layer_count(self) -> int:
        return 5

    def total_bottom_exposure_s(self) -> float:
        return round(self.bottom_layer_exposure_s() * self.bottom_layer_count(), 1)

    def total_layers(self, part_height_mm: float = 50.0) -> int:
        if self.layer_thickness_mm <= 0:
            return 0
        return int(part_height_mm / self.layer_thickness_mm)

    def total_print_time_min(self, part_height_mm: float = 50.0, lift_time_s: float = 6.0) -> float:
        layers = self.total_layers(part_height_mm)
        normal_layers = max(0, layers - self.bottom_layer_count())
        total_s = (self.bottom_layer_count() * (self.bottom_layer_exposure_s() + lift_time_s) +
                   normal_layers * (self.exposure_time_s() + lift_time_s))
        return round(total_s / 60, 2)

    def energy_per_layer_mj(self, layer_area_mm2: float = 10000) -> float:
        power = 5.0
        return round(power * self.exposure_time_s() * layer_area_mm2 / 1e6 / 1000, 6)

    def stats(self, part_height_mm: float = 50.0) -> Dict[str, float]:
        return {
            "exposure_time_s": self.exposure_time_s(),
            "total_layers": self.total_layers(part_height_mm),
            "total_print_time_min": self.total_print_time_min(part_height_mm),
        }

    def run(self):
        print("=" * 60)
        print("SLA RESIN EXPOSURE CALCULATOR")
        print("=" * 60)
        sla = SLAResinExposure(layer_thickness_mm=0.05, resin_type="standard")
        print(f"Resin: {sla.resin_type}")
        print(f"Layer: {sla.layer_thickness_mm} mm")
        print(f"Exposure: {sla.exposure_time_s():.2f} s")
        print(f"Bottom exposure: {sla.bottom_layer_exposure_s():.1f} s x {sla.bottom_layer_count()}")
        print(f"Layers (50mm): {sla.total_layers(50)}")
        print(f"Print time: {sla.total_print_time_min(50):.2f} min")
        print(f"Stats: {sla.stats(50)}")

if __name__ == "__main__":
    SLAResinExposure(0).run()
