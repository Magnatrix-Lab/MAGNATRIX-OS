"""Dough Calculator — hydration, bakers %, scaling, yield, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class DoughCalculator:
    flour_g: float = 1000.0
    hydration_pct: float = 65.0
    salt_pct: float = 2.0
    yeast_pct: float = 1.0
    fat_pct: float = 0.0

    def water_g(self) -> float:
        return self.flour_g * self.hydration_pct / 100

    def salt_g(self) -> float:
        return self.flour_g * self.salt_pct / 100

    def yeast_g(self) -> float:
        return self.flour_g * self.yeast_pct / 100

    def fat_g(self) -> float:
        return self.flour_g * self.fat_pct / 100

    def total_dough(self) -> float:
        return self.flour_g + self.water_g() + self.salt_g() + self.yeast_g() + self.fat_g()

    def scale(self, target_dough_g: float) -> Dict[str, float]:
        factor = target_dough_g / self.total_dough()
        return {
            "flour": self.flour_g * factor,
            "water": self.water_g() * factor,
            "salt": self.salt_g() * factor,
            "yeast": self.yeast_g() * factor,
            "fat": self.fat_g() * factor,
        }

    def loaf_count(self, loaf_weight: float = 500) -> int:
        return int(self.total_dough() / loaf_weight)

    def stats(self) -> Dict:
        return {"total": round(self.total_dough(), 1), "hydration": self.hydration_pct, "loaves": self.loaf_count()}

def run():
    dc = DoughCalculator(flour_g=500, hydration_pct=70, salt_pct=2, yeast_pct=1, fat_pct=3)
    print(dc.stats())
    print("Scale to 2000g:", dc.scale(2000))

if __name__ == "__main__":
    run()
