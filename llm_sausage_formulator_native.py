"""Native stdlib module: Sausage Formulator
Calculates meat-to-fat ratios, binder percentages, and spice blends for sausage batches.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class SausageType(Enum):
    FRESH = "fresh"
    SMOKED = "smoked"
    DRIED = "dried"
    COOKED = "cooked"

@dataclass
class Ingredient:
    name: str
    weight_g: float
    pct: float

@dataclass
class SausageFormulator:
    batch_name: str
    total_weight_g: float
    meat_pct: float = 70.0
    fat_pct: float = 25.0
    binder_pct: float = 3.0
    seasonings: List[Ingredient] = field(default_factory=list)

    def meat_weight(self) -> float:
        return self.total_weight_g * (self.meat_pct / 100)

    def fat_weight(self) -> float:
        return self.total_weight_g * (self.fat_pct / 100)

    def binder_weight(self) -> float:
        return self.total_weight_g * (self.binder_pct / 100)

    def seasoning_weight(self) -> float:
        return sum(s.weight_g for s in self.seasonings)

    def stats(self) -> Dict[str, float]:
        return {
            "meat_g": round(self.meat_weight(), 1),
            "fat_g": round(self.fat_weight(), 1),
            "binder_g": round(self.binder_weight(), 1),
            "seasoning_g": round(self.seasoning_weight(), 1),
            "total_g": round(self.total_weight_g, 1),
        }

def run():
    sf = SausageFormulator(
        batch_name="Italian Sweet",
        total_weight_g=5000,
        meat_pct=72,
        fat_pct=23,
        binder_pct=2.5,
        seasonings=[
            Ingredient("salt", 100, 2.0),
            Ingredient("fennel", 30, 0.6),
            Ingredient("paprika", 15, 0.3),
        ]
    )
    print(sf.stats())

if __name__ == "__main__":
    run()
