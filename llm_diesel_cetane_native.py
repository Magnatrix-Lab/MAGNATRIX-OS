"""Diesel Cetane Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class DieselCetane:
    cetane_number: float
    density_kg_m3: float = 835.0
    biodiesel_percent: float = 0.0
    aromatic_percent: float = 25.0

    def cetane_index(self) -> float:
        api = 141.5 / (self.density_kg_m3 / 1000.0) - 131.5
        aniline = 180 - 1.5 * api
        ci = 95.9 - 0.042 * aniline + 0.032 * api
        return round(max(ci, 30), 1)

    def ignition_delay_ms(self) -> float:
        base = 3.0
        return round(base * math.exp((50 - self.cetane_number) / 15.0), 2)

    def combustion_quality_index(self) -> float:
        return round(self.cetane_number * (1 - self.aromatic_percent / 200.0), 2)

    def blended_cetane(self, other_cetane: float, other_fraction: float) -> float:
        if other_fraction < 0 or other_fraction > 1:
            return self.cetane_number
        return round(self.cetane_number * (1 - other_fraction) + other_cetane * other_fraction, 1)

    def biodiesel_adjusted_cetane(self) -> float:
        bio_cetane = 55.0
        if self.biodiesel_percent <= 0:
            return self.cetane_number
        return round(self.cetane_number * (1 - self.biodiesel_percent / 100.0) + bio_cetane * (self.biodiesel_percent / 100.0), 1)

    def cold_filter_plugging_point_c(self) -> float:
        return round(15 - self.cetane_number * 0.15, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "cetane_number": self.cetane_number,
            "cetane_index": self.cetane_index(),
            "ignition_delay_ms": self.ignition_delay_ms(),
        }

    def run(self):
        print("=" * 60)
        print("DIESEL CETANE CALCULATOR")
        print("=" * 60)
        diesel = DieselCetane(
            cetane_number=51, density_kg_m3=840,
            biodiesel_percent=20, aromatic_percent=20
        )
        print(f"Cetane number: {diesel.cetane_number}")
        print(f"Cetane index: {diesel.cetane_index():.1f}")
        print(f"Ignition delay: {diesel.ignition_delay_ms():.2f} ms")
        print(f"Combustion quality: {diesel.combustion_quality_index():.2f}")
        print(f"Bio adjusted: {diesel.biodiesel_adjusted_cetane():.1f}")
        print(f"CFPP: {diesel.cold_filter_plugging_point_c():.1f} C")
        print(f"Stats: {diesel.stats()}")

if __name__ == "__main__":
    DieselCetane(0).run()
