"""Fuel Octane Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FuelOctane:
    ron: float
    mon: float
    ethanol_percent: float = 0.0
    lead_substitute: bool = False

    def anti_knock_index(self) -> float:
        return round((self.ron + self.mon) / 2.0, 1)

    def sensitivity(self) -> float:
        return round(self.ron - self.mon, 1)

    def blended_ron(self, other_ron: float, other_fraction: float) -> float:
        if other_fraction < 0 or other_fraction > 1:
            return self.ron
        return round(self.ron * (1 - other_fraction) + other_ron * other_fraction, 1)

    def ethanol_adjusted_ron(self) -> float:
        ethanol_ron = 109.0
        if self.ethanol_percent <= 0:
            return self.ron
        return round(self.ron * (1 - self.ethanol_percent / 100.0) + ethanol_ron * (self.ethanol_percent / 100.0), 1)

    def octane_requirement(self, compression_ratio: float = 10.0) -> float:
        return round(60 + 5 * (compression_ratio - 8), 1)

    def is_sufficient_for(self, compression_ratio: float = 10.0) -> bool:
        return self.ron >= self.octane_requirement(compression_ratio)

    def stats(self) -> Dict[str, float]:
        return {
            "ron": self.ron,
            "mon": self.mon,
            "anti_knock_index": self.anti_knock_index(),
            "sensitivity": self.sensitivity(),
        }

    def run(self):
        print("=" * 60)
        print("FUEL OCTANE CALCULATOR")
        print("=" * 60)
        fuel = FuelOctane(ron=95, mon=85, ethanol_percent=10)
        print(f"RON: {fuel.ron}, MON: {fuel.mon}")
        print(f"AKI: {fuel.anti_knock_index():.1f}")
        print(f"Sensitivity: {fuel.sensitivity():.1f}")
        print(f"Ethanol adjusted RON: {fuel.ethanol_adjusted_ron():.1f}")
        print(f"Octane requirement (CR 10): {fuel.octane_requirement(10.0):.1f}")
        print(f"Sufficient for CR 10: {fuel.is_sufficient_for(10.0)}")
        print(f"Blended RON (98 @ 20%): {fuel.blended_ron(98, 0.2):.1f}")
        print(f"Stats: {fuel.stats()}")

if __name__ == "__main__":
    FuelOctane(0, 0).run()
