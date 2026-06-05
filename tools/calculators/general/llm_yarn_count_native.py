"""Yarn Count Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class YarnCount:
    length_m: float
    mass_g: float
    count_system: str = "tex"

    def tex(self) -> float:
        if self.length_m <= 0:
            return 0.0
        return round(self.mass_g / self.length_m * 1000, 2)

    def denier(self) -> float:
        if self.length_m <= 0:
            return 0.0
        return round(self.mass_g / self.length_m * 9000, 1)

    def metric_count(self) -> float:
        if self.mass_g <= 0:
            return 0.0
        return round(self.length_m / self.mass_g * 1000, 2)

    def cotton_count(self) -> float:
        if self.mass_g <= 0:
            return 0.0
        return round(self.length_m * 1.693 / self.mass_g, 2)

    def worsted_count(self) -> float:
        if self.mass_g <= 0:
            return 0.0
        return round(self.length_m * 1.133 / self.mass_g, 2)

    def convert_to(self, target_system: str) -> float:
        tex_val = self.tex()
        if tex_val <= 0:
            return 0.0
        conversions = {
            "tex": tex_val,
            "denier": tex_val * 9,
            "metric": 1000 / tex_val if tex_val > 0 else 0,
            "cotton": 590.5 / tex_val if tex_val > 0 else 0,
            "worsted": 885.8 / tex_val if tex_val > 0 else 0,
        }
        result = conversions.get(target_system, tex_val)
        return round(result, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "tex": self.tex(),
            "denier": self.denier(),
            "metric_count": self.metric_count(),
        }

    def run(self):
        print("=" * 60)
        print("YARN COUNT CALCULATOR")
        print("=" * 60)
        yarn = YarnCount(length_m=1000, mass_g=20, count_system="tex")
        print(f"Length: {yarn.length_m} m, Mass: {yarn.mass_g} g")
        print(f"Tex: {yarn.tex():.2f}")
        print(f"Denier: {yarn.denier():.1f}")
        print(f"Metric count (Nm): {yarn.metric_count():.2f}")
        print(f"Cotton count (Ne): {yarn.cotton_count():.2f}")
        print(f"Worsted count: {yarn.worsted_count():.2f}")
        print(f"Convert to cotton: {yarn.convert_to('cotton'):.2f}")
        print(f"Stats: {yarn.stats()}")

if __name__ == "__main__":
    YarnCount(0, 0).run()
