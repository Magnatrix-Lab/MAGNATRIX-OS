"""Native stdlib module: Bottling Calculator
Calculates bottling needs, fill levels, and cork/shell selection for wine.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class BottleSize(Enum):
    SPLIT = 187
    HALF = 375
    STANDARD = 750
    MAGNUM = 1500
    DOUBLE_MAGNUM = 3000

@dataclass
class BottlingCalculator:
    wine_volume_l: float
    bottle_size_ml: int = 750
    headspace_ml: int = 10
    wastage_pct: float = 2.0

    def effective_bottle_volume_ml(self) -> float:
        return self.bottle_size_ml - self.headspace_ml

    def bottles_needed(self) -> int:
        if self.effective_bottle_volume_ml() == 0:
            return 0
        wine_ml = self.wine_volume_l * 1000 * (1 + self.wastage_pct / 100)
        return int(wine_ml / self.effective_bottle_volume_ml()) + (1 if wine_ml % self.effective_bottle_volume_ml() > 0 else 0)

    def wine_remaining_ml(self) -> float:
        if self.effective_bottle_volume_ml() == 0:
            return 0.0
        wine_ml = self.wine_volume_l * 1000
        bottles = self.bottles_needed()
        used = bottles * self.effective_bottle_volume_ml()
        return max(0, wine_ml - used)

    def bottles_by_size(self) -> Dict[str, int]:
        sizes = {}
        for size in BottleSize:
            self.bottle_size_ml = size.value
            sizes[size.name] = self.bottles_needed()
        return sizes

    def stats(self) -> Dict:
        return {
            "wine_volume_l": self.wine_volume_l,
            "bottle_size_ml": self.bottle_size_ml,
            "headspace_ml": self.headspace_ml,
            "bottles_needed": self.bottles_needed(),
            "wine_remaining_ml": round(self.wine_remaining_ml(), 1),
        }

def run():
    btl = BottlingCalculator(wine_volume_l=225, bottle_size_ml=750, headspace_ml=10, wastage_pct=2)
    print(btl.stats())

if __name__ == "__main__":
    run()
