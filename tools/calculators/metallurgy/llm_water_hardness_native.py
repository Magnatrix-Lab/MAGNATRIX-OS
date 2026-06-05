"""Water Hardness Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class WaterHardness:
    calcium_mg_l: float
    magnesium_mg_l: float
    iron_mg_l: float = 0.0
    manganese_mg_l: float = 0.0

    def calcium_hardness_mg_l_caco3(self) -> float:
        return round(self.calcium_mg_l * 2.497, 2)

    def magnesium_hardness_mg_l_caco3(self) -> float:
        return round(self.magnesium_mg_l * 4.118, 2)

    def total_hardness_mg_l_caco3(self) -> float:
        return round(self.calcium_hardness_mg_l_caco3() + self.magnesium_hardness_mg_l_caco3(), 2)

    def hardness_grains_per_gallon(self) -> float:
        return round(self.total_hardness_mg_l_caco3() / 17.1, 2)

    def hardness_mmol_l(self) -> float:
        return round(self.total_hardness_mg_l_caco3() / 100.09, 3)

    def hardness_german_degrees(self) -> float:
        return round(self.total_hardness_mg_l_caco3() / 17.848, 2)

    def hardness_classification(self) -> str:
        total = self.total_hardness_mg_l_caco3()
        if total < 60:
            return "soft"
        elif total < 120:
            return "moderately_hard"
        elif total < 180:
            return "hard"
        else:
            return "very_hard"

    def lime_required_kg_per_m3(self) -> float:
        return round(self.total_hardness_mg_l_caco3() / 1000.0 * 0.74, 4)

    def stats(self) -> Dict[str, float]:
        return {
            "total_hardness_mg_l_caco3": self.total_hardness_mg_l_caco3(),
            "hardness_grains_per_gallon": self.hardness_grains_per_gallon(),
            "hardness_german_degrees": self.hardness_german_degrees(),
        }

    def run(self):
        print("=" * 60)
        print("WATER HARDNESS CALCULATOR")
        print("=" * 60)
        wh = WaterHardness(calcium_mg_l=80, magnesium_mg_l=30, iron_mg_l=0.5)
        print(f"Ca: {wh.calcium_mg_l} mg/L, Mg: {wh.magnesium_mg_l} mg/L")
        print(f"Ca hardness: {wh.calcium_hardness_mg_l_caco3():.2f} mg/L CaCO3")
        print(f"Mg hardness: {wh.magnesium_hardness_mg_l_caco3():.2f} mg/L CaCO3")
        print(f"Total hardness: {wh.total_hardness_mg_l_caco3():.2f} mg/L CaCO3")
        print(f"Grains/gallon: {wh.hardness_grains_per_gallon():.2f}")
        print(f"mmol/L: {wh.hardness_mmol_l():.3f}")
        print(f"German degrees: {wh.hardness_german_degrees():.2f}")
        print(f"Classification: {wh.hardness_classification()}")
        print(f"Stats: {wh.stats()}")

if __name__ == "__main__":
    WaterHardness(0, 0).run()
