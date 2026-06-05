"""Tread Wear Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class TreadWear:
    initial_tread_depth_mm: float
    current_tread_depth_mm: float
    distance_km: float
    tire_position: str = "front"
    load_kg: float = 500.0

    def wear_rate_mm_per_1000km(self) -> float:
        worn = self.initial_tread_depth_mm - self.current_tread_depth_mm
        if self.distance_km <= 0:
            return 0.0
        return round(worn / self.distance_km * 1000, 3)

    def percent_worn(self) -> float:
        if self.initial_tread_depth_mm <= 0:
            return 0.0
        worn = self.initial_tread_depth_mm - self.current_tread_depth_mm
        return round(worn / self.initial_tread_depth_mm * 100, 2)

    def remaining_life_km(self) -> float:
        rate = self.wear_rate_mm_per_1000km()
        if rate <= 0:
            return float('inf')
        return round(self.current_tread_depth_mm / rate * 1000, 1)

    def wear_index(self) -> float:
        load_factor = 1 + (self.load_kg - 500) / 2000
        wear = self.wear_rate_mm_per_1000km() * load_factor
        return round(wear, 3)

    def stats(self) -> Dict[str, float]:
        return {
            "wear_rate_mm_per_1000km": self.wear_rate_mm_per_1000km(),
            "percent_worn": self.percent_worn(),
            "remaining_life_km": self.remaining_life_km() if self.remaining_life_km() != float('inf') else 999999,
        }

    def run(self):
        print("=" * 60)
        print("TREAD WEAR CALCULATOR")
        print("=" * 60)
        wear = TreadWear(
            initial_tread_depth_mm=8.0, current_tread_depth_mm=5.5,
            distance_km=25000, tire_position="rear", load_kg=700
        )
        print(f"Initial depth: {wear.initial_tread_depth_mm} mm")
        print(f"Current depth: {wear.current_tread_depth_mm} mm")
        print(f"Distance driven: {wear.distance_km} km")
        print(f"Wear rate: {wear.wear_rate_mm_per_1000km():.3f} mm/1000km")
        print(f"Percent worn: {wear.percent_worn():.2f}%")
        print(f"Remaining life: {wear.remaining_life_km():.1f} km")
        print(f"Wear index: {wear.wear_index():.3f}")
        print(f"Stats: {wear.stats()}")

if __name__ == "__main__":
    TreadWear(0, 0, 0).run()
