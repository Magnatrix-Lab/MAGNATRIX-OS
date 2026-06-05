"""3D Print Time Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class Print3DTime:
    part_height_mm: float
    layer_height_mm: float
    layer_print_time_s: float
    infill_percent: float = 20.0
    support_percent: float = 10.0

    def total_layers(self) -> int:
        if self.layer_height_mm <= 0:
            return 0
        return int(self.part_height_mm / self.layer_height_mm)

    def print_time_hours(self) -> float:
        layers = self.total_layers()
        factor = 1 + self.infill_percent / 100.0 + self.support_percent / 100.0
        return round(layers * self.layer_print_time_s * factor / 3600, 2)

    def warmup_time_min(self) -> float:
        return 5.0

    def cooldown_time_min(self) -> float:
        return 10.0

    def total_time_hours(self) -> float:
        return round(self.print_time_hours() + (self.warmup_time_min() + self.cooldown_time_min()) / 60.0, 2)

    def print_speed_mm_per_s(self, layer_area_mm2: float = 10000) -> float:
        if self.layer_print_time_s <= 0:
            return 0.0
        return round(layer_area_mm2 * self.layer_height_mm / self.layer_print_time_s, 2)

    def cost_per_part(self, machine_rate_per_h: float = 10.0, material_cost: float = 5.0) -> float:
        return round(self.total_time_hours() * machine_rate_per_h + material_cost, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "total_layers": self.total_layers(),
            "print_time_hours": self.print_time_hours(),
            "total_time_hours": self.total_time_hours(),
        }

    def run(self):
        print("=" * 60)
        print("3D PRINT TIME CALCULATOR")
        print("=" * 60)
        pt = Print3DTime(
            part_height_mm=100, layer_height_mm=0.2,
            layer_print_time_s=30, infill_percent=25, support_percent=15
        )
        print(f"Height: {pt.part_height_mm} mm, Layer: {pt.layer_height_mm} mm")
        print(f"Layers: {pt.total_layers()}")
        print(f"Print time: {pt.print_time_hours():.2f} h")
        print(f"Total time: {pt.total_time_hours():.2f} h")
        print(f"Print speed: {pt.print_speed_mm_per_s():.2f} mm3/s")
        print(f"Cost: ${pt.cost_per_part():.2f}")
        print(f"Stats: {pt.stats()}")

if __name__ == "__main__":
    Print3DTime(0, 0, 0).run()
