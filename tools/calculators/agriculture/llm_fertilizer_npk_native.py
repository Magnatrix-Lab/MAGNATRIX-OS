"""Fertilizer NPK Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FertilizerNPK:
    nitrogen_percent: float
    phosphorus_percent: float
    potassium_percent: float
    application_rate_kg_per_ha: float
    area_ha: float

    def npk_ratio(self) -> str:
        from math import gcd
        a, b, c = int(self.nitrogen_percent), int(self.phosphorus_percent), int(self.potassium_percent)
        g = gcd(gcd(a, b), c) if a > 0 and b > 0 and c > 0 else 1
        return f"{a//g}-{b//g}-{c//g}"

    def total_fertilizer_kg(self) -> float:
        return round(self.application_rate_kg_per_ha * self.area_ha, 2)

    def nitrogen_kg(self) -> float:
        return round(self.total_fertilizer_kg() * self.nitrogen_percent / 100.0, 2)

    def phosphorus_kg(self) -> float:
        return round(self.total_fertilizer_kg() * self.phosphorus_percent / 100.0, 2)

    def potassium_kg(self) -> float:
        return round(self.total_fertilizer_kg() * self.potassium_percent / 100.0, 2)

    def p2o5_equivalent_kg(self) -> float:
        return round(self.phosphorus_kg() * 2.29, 2)

    def k2o_equivalent_kg(self) -> float:
        return round(self.potassium_kg() * 1.20, 2)

    def cost_estimate(self, price_per_kg: float = 0.5) -> float:
        return round(self.total_fertilizer_kg() * price_per_kg, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "total_fertilizer_kg": self.total_fertilizer_kg(),
            "nitrogen_kg": self.nitrogen_kg(),
            "phosphorus_kg": self.phosphorus_kg(),
            "potassium_kg": self.potassium_kg(),
        }

    def run(self):
        print("=" * 60)
        print("FERTILIZER NPK CALCULATOR")
        print("=" * 60)
        npk = FertilizerNPK(
            nitrogen_percent=15, phosphorus_percent=15, potassium_percent=15,
            application_rate_kg_per_ha=200, area_ha=5
        )
        print(f"NPK: {npk.nitrogen_percent}-{npk.phosphorus_percent}-{npk.potassium_percent}")
        print(f"Ratio: {npk.npk_ratio()}")
        print(f"Total fertilizer: {npk.total_fertilizer_kg():.2f} kg")
        print(f"N: {npk.nitrogen_kg():.2f} kg, P: {npk.phosphorus_kg():.2f} kg, K: {npk.potassium_kg():.2f} kg")
        print(f"P2O5: {npk.p2o5_equivalent_kg():.2f} kg, K2O: {npk.k2o_equivalent_kg():.2f} kg")
        print(f"Cost: ${npk.cost_estimate():.2f}")
        print(f"Stats: {npk.stats()}")

if __name__ == "__main__":
    FertilizerNPK(0, 0, 0, 0, 0).run()
