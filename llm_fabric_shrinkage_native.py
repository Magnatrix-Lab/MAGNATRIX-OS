"""Fabric Shrinkage Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FabricShrinkage:
    original_length_cm: float
    washed_length_cm: float
    original_width_cm: float
    washed_width_cm: float
    wash_cycles: int = 1

    def length_shrinkage_percent(self) -> float:
        if self.original_length_cm <= 0:
            return 0.0
        return round((self.original_length_cm - self.washed_length_cm) / self.original_length_cm * 100, 2)

    def width_shrinkage_percent(self) -> float:
        if self.original_width_cm <= 0:
            return 0.0
        return round((self.original_width_cm - self.washed_width_cm) / self.original_width_cm * 100, 2)

    def area_change_percent(self) -> float:
        orig_area = self.original_length_cm * self.original_width_cm
        washed_area = self.washed_length_cm * self.washed_width_cm
        if orig_area <= 0:
            return 0.0
        return round((orig_area - washed_area) / orig_area * 100, 2)

    def shrinkage_per_cycle(self) -> Dict[str, float]:
        if self.wash_cycles <= 0:
            return {"length": 0.0, "width": 0.0}
        return {
            "length": round(self.length_shrinkage_percent() / self.wash_cycles, 2),
            "width": round(self.width_shrinkage_percent() / self.wash_cycles, 2),
        }

    def dimensional_stability_index(self) -> float:
        ls = self.length_shrinkage_percent()
        ws = self.width_shrinkage_percent()
        return round(100 - (ls + ws) / 2, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "length_shrinkage_percent": self.length_shrinkage_percent(),
            "width_shrinkage_percent": self.width_shrinkage_percent(),
            "area_change_percent": self.area_change_percent(),
        }

    def run(self):
        print("=" * 60)
        print("FABRIC SHRINKAGE CALCULATOR")
        print("=" * 60)
        shr = FabricShrinkage(
            original_length_cm=100.0, washed_length_cm=95.0,
            original_width_cm=100.0, washed_width_cm=96.0, wash_cycles=3
        )
        print(f"Original: {shr.original_length_cm}x{shr.original_width_cm} cm")
        print(f"After wash: {shr.washed_length_cm}x{shr.washed_width_cm} cm")
        print(f"Length shrinkage: {shr.length_shrinkage_percent():.2f}%")
        print(f"Width shrinkage: {shr.width_shrinkage_percent():.2f}%")
        print(f"Area change: {shr.area_change_percent():.2f}%")
        print(f"Per cycle: {shr.shrinkage_per_cycle()}")
        print(f"Stability index: {shr.dimensional_stability_index():.2f}")
        print(f"Stats: {shr.stats()}")

if __name__ == "__main__":
    FabricShrinkage(0, 0, 0, 0).run()
