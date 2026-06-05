"""Glue Mixing Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class GlueMixing:
    resin_weight_g: float
    hardener_ratio: float = 2.0
    filler_percent: float = 0.0
    solvent_percent: float = 0.0

    def hardener_weight_g(self) -> float:
        return round(self.resin_weight_g / self.hardener_ratio, 2)

    def filler_weight_g(self) -> float:
        return round((self.resin_weight_g + self.hardener_weight_g()) * self.filler_percent / 100.0, 2)

    def solvent_weight_g(self) -> float:
        return round((self.resin_weight_g + self.hardener_weight_g()) * self.solvent_percent / 100.0, 2)

    def total_weight_g(self) -> float:
        return round(self.resin_weight_g + self.hardener_weight_g() + self.filler_weight_g() + self.solvent_weight_g(), 2)

    def mix_ratio(self) -> Dict[str, float]:
        total = self.total_weight_g()
        if total <= 0:
            return {}
        return {
            "resin": round(self.resin_weight_g / total * 100, 2),
            "hardener": round(self.hardener_weight_g() / total * 100, 2),
            "filler": round(self.filler_weight_g() / total * 100, 2),
            "solvent": round(self.solvent_weight_g() / total * 100, 2),
        }

    def pot_life_minutes(self, base_pot_life: float = 45.0) -> float:
        factor = 1.0 + self.filler_percent / 100.0 + self.solvent_percent / 50.0
        return round(base_pot_life / factor, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "hardener_weight_g": self.hardener_weight_g(),
            "total_weight_g": self.total_weight_g(),
            "pot_life_minutes": self.pot_life_minutes(),
        }

    def run(self):
        print("=" * 60)
        print("GLUE MIXING CALCULATOR")
        print("=" * 60)
        glue = GlueMixing(
            resin_weight_g=100.0, hardener_ratio=2.0,
            filler_percent=15.0, solvent_percent=10.0
        )
        print(f"Resin: {glue.resin_weight_g} g")
        print(f"Hardener ratio: 1:{glue.hardener_ratio}")
        print(f"Hardener weight: {glue.hardener_weight_g():.2f} g")
        print(f"Filler: {glue.filler_weight_g():.2f} g")
        print(f"Solvent: {glue.solvent_weight_g():.2f} g")
        print(f"Total: {glue.total_weight_g():.2f} g")
        print(f"Mix ratio: {glue.mix_ratio()}")
        print(f"Pot life: {glue.pot_life_minutes():.1f} min")
        print(f"Stats: {glue.stats()}")

if __name__ == "__main__":
    GlueMixing(0).run()
