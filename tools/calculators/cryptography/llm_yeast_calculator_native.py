"""Yeast Calculator — cell count, viability, pitching rate, starter, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class YeastCalculator:
    original_gravity: float = 1.050
    volume_l: float = 20.0
    viability_pct: float = 90.0
    yeast_type: str = "liquid"

    def cells_needed(self) -> float:
        """Million cells per mL per degree Plato"""
        plato = (self.original_gravity - 1) * 250
        return 0.75 * plato * self.volume_l * 1000

    def cells_per_pack(self) -> float:
        if self.yeast_type == "liquid":
            return 100
        return 200

    def packs_needed(self) -> float:
        available = self.cells_per_pack() * self.viability_pct / 100
        return self.cells_needed() / available if available > 0 else 0.0

    def starter_size(self, target_growth: float = 2.0) -> float:
        base = self.volume_l * 0.5
        return base * target_growth

    def aeration_required(self) -> str:
        if self.original_gravity > 1.060:
            return "oxygen"
        return "air"

    def stats(self) -> Dict:
        return {"cells_needed": round(self.cells_needed(), 0), "packs": round(self.packs_needed(), 1), "starter": round(self.starter_size(), 1), "aeration": self.aeration_required()}

def run():
    yc = YeastCalculator(original_gravity=1.080, volume_l=25, viability_pct=80, yeast_type="liquid")
    print(yc.stats())

if __name__ == "__main__":
    run()
