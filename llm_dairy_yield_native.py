"""Native stdlib module: Dairy Yield Calculator
Estimates milk production, butterfat yield, and protein yield per lactation.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class Breed(Enum):
    HOLSTEIN = "holstein"
    JERSEY = "jersey"
    GUERNSEY = "guernsey"
    AYRSHIRE = "ayrshire"

@dataclass
class DairyYield:
    breed: Breed
    lactation_days: int
    daily_avg_liters: float
    fat_pct: float
    protein_pct: float

    def total_milk_liters(self) -> float:
        return self.lactation_days * self.daily_avg_liters

    def fat_kg(self) -> float:
        return self.total_milk_liters() * (self.fat_pct / 100)

    def protein_kg(self) -> float:
        return self.total_milk_liters() * (self.protein_pct / 100)

    def solids_kg(self) -> float:
        return self.fat_kg() + self.protein_kg()

    def stats(self) -> Dict[str, float]:
        return {
            "total_milk_l": round(self.total_milk_liters(), 1),
            "fat_kg": round(self.fat_kg(), 2),
            "protein_kg": round(self.protein_kg(), 2),
            "solids_kg": round(self.solids_kg(), 2),
        }

def run():
    dy = DairyYield(breed=Breed.HOLSTEIN, lactation_days=305, daily_avg_liters=30, fat_pct=3.8, protein_pct=3.2)
    print(dy.stats())

if __name__ == "__main__":
    run()
