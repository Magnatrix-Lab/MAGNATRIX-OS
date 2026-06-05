"""Weld Symbol Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class WeldSymbol:
    weld_type: str
    leg_size_mm: float
    throat_size_mm: float = 0.0
    length_mm: float = 100.0
    intermittent: bool = False
    pitch_mm: float = 0.0

    def actual_throat_mm(self) -> float:
        if self.throat_size_mm > 0:
            return self.throat_size_mm
        return round(self.leg_size_mm * 0.707, 2)

    def weld_area_mm2(self) -> float:
        if self.weld_type == "fillet":
            return round(self.leg_size_mm * self.actual_throat_mm() / 2, 2)
        elif self.weld_type == "groove":
            return round(self.leg_size_mm * self.throat_size_mm, 2)
        else:
            return round(self.leg_size_mm ** 2, 2)

    def total_weld_length_mm(self) -> float:
        if self.intermittent and self.pitch_mm > 0:
            segments = int(self.length_mm / self.pitch_mm)
            return round(segments * self.leg_size_mm, 2)
        return self.length_mm

    def total_weld_volume_mm3(self) -> float:
        return round(self.weld_area_mm2() * self.total_weld_length_mm(), 2)

    def weld_weight_kg(self, density_g_cm3: float = 7.8) -> float:
        return round(self.total_weld_volume_mm3() * density_g_cm3 / 1e6, 4)

    def strength_kn(self, allowable_stress_mpa: float = 110.0) -> float:
        area = self.weld_area_mm2()
        return round(area * allowable_stress_mpa / 1000, 2)

    def is_continuous(self) -> bool:
        return not self.intermittent

    def weld_symbol_string(self) -> str:
        if self.intermittent:
            return f"{self.weld_type} {self.leg_size_mm}mm L={self.length_mm}mm P={self.pitch_mm}mm"
        return f"{self.weld_type} {self.leg_size_mm}mm L={self.length_mm}mm"

    def stats(self) -> Dict[str, float]:
        return {
            "weld_area_mm2": self.weld_area_mm2(),
            "total_weld_volume_mm3": self.total_weld_volume_mm3(),
            "strength_kn": self.strength_kn(),
        }

    def run(self):
        print("=" * 60)
        print("WELD SYMBOL CALCULATOR")
        print("=" * 60)
        ws = WeldSymbol(
            weld_type="fillet", leg_size_mm=6, length_mm=200,
            intermittent=False
        )
        print(f"Weld: {ws.weld_symbol_string()}")
        print(f"Throat: {ws.actual_throat_mm():.2f} mm")
        print(f"Area: {ws.weld_area_mm2():.2f} mm2")
        print(f"Length: {ws.total_weld_length_mm():.2f} mm")
        print(f"Volume: {ws.total_weld_volume_mm3():.2f} mm3")
        print(f"Weight: {ws.weld_weight_kg():.4f} kg")
        print(f"Strength: {ws.strength_kn():.2f} kN")
        print(f"Stats: {ws.stats()}")

if __name__ == "__main__":
    WeldSymbol("fillet", 0).run()
