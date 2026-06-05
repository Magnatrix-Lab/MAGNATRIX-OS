"""3D Print Material Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class Print3DMaterial:
    part_volume_cm3: float
    material_type: str = "pla"
    infill_percent: float = 20.0
    wall_thickness_mm: float = 1.2
    support_percent: float = 10.0

    def material_density_g_cm3(self) -> float:
        densities = {"pla": 1.24, "abs": 1.04, "petg": 1.27, "nylon": 1.15, "tpu": 1.21, "pc": 1.20, "resin": 1.10}
        return densities.get(self.material_type, 1.24)

    def infill_volume_cm3(self) -> float:
        return round(self.part_volume_cm3 * self.infill_percent / 100.0, 2)

    def wall_volume_cm3(self) -> float:
        return round(self.part_volume_cm3 * 0.15 * (self.wall_thickness_mm / 1.2), 2)

    def support_volume_cm3(self) -> float:
        return round(self.part_volume_cm3 * self.support_percent / 100.0, 2)

    def total_material_volume_cm3(self) -> float:
        return round(self.infill_volume_cm3() + self.wall_volume_cm3() + self.support_volume_cm3(), 2)

    def total_material_weight_g(self) -> float:
        return round(self.total_material_volume_cm3() * self.material_density_g_cm3(), 2)

    def filament_length_m(self, filament_diameter_mm: float = 1.75) -> float:
        cross_section = math.pi * (filament_diameter_mm / 2) ** 2
        if cross_section <= 0:
            return 0.0
        volume_mm3 = self.total_material_volume_cm3() * 1000
        return round(volume_mm3 / cross_section / 1000, 2)

    def material_cost(self, price_per_kg: float = 25.0) -> float:
        return round(self.total_material_weight_g() / 1000.0 * price_per_kg, 2)

    def waste_percent(self) -> float:
        if self.part_volume_cm3 <= 0:
            return 0.0
        return round(self.support_volume_cm3() / self.total_material_volume_cm3() * 100, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "total_material_weight_g": self.total_material_weight_g(),
            "filament_length_m": self.filament_length_m(),
            "material_cost": self.material_cost(),
        }

    def run(self):
        print("=" * 60)
        print("3D PRINT MATERIAL CALCULATOR")
        print("=" * 60)
        pm = Print3DMaterial(
            part_volume_cm3=50, material_type="pla",
            infill_percent=20, wall_thickness_mm=1.2, support_percent=15
        )
        print(f"Volume: {pm.part_volume_cm3} cm3, Material: {pm.material_type}")
        print(f"Density: {pm.material_density_g_cm3():.2f} g/cm3")
        print(f"Total material: {pm.total_material_weight_g():.2f} g")
        print(f"Filament length: {pm.filament_length_m():.2f} m")
        print(f"Material cost: ${pm.material_cost():.2f}")
        print(f"Waste: {pm.waste_percent():.2f}%")
        print(f"Stats: {pm.stats()}")

if __name__ == "__main__":
    Print3DMaterial(0).run()
