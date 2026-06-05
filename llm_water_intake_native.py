"""Native stdlib module: Water Intake Calculator
Calculates daily water intake recommendations by weight, activity, and climate.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class Climate(Enum):
    TEMPERATE = "temperate"
    HOT = "hot"
    COLD = "cold"
    HUMID = "humid"

@dataclass
class WaterIntakeCalculator:
    weight_kg: float
    climate: Climate
    exercise_min: float = 0.0
    is_pregnant: bool = False
    is_breastfeeding: bool = False

    def base_intake_ml(self) -> float:
        return self.weight_kg * 35

    def climate_adjustment_ml(self) -> float:
        adjustments = {Climate.TEMPERATE: 0, Climate.HOT: 500, Climate.COLD: 0, Climate.HUMID: 300}
        return adjustments.get(self.climate, 0)

    def exercise_adjustment_ml(self) -> float:
        return self.exercise_min * 10

    def total_intake_ml(self) -> float:
        total = self.base_intake_ml() + self.climate_adjustment_ml() + self.exercise_adjustment_ml()
        if self.is_pregnant:
            total += 300
        if self.is_breastfeeding:
            total += 700
        return total

    def glasses_per_day(self, glass_size_ml: float = 250) -> float:
        if glass_size_ml == 0:
            return 0.0
        return self.total_intake_ml() / glass_size_ml

    def stats(self) -> Dict:
        return {
            "base_intake_ml": round(self.base_intake_ml(), 1),
            "climate_adjustment_ml": self.climate_adjustment_ml(),
            "exercise_adjustment_ml": self.exercise_adjustment_ml(),
            "total_intake_ml": round(self.total_intake_ml(), 1),
            "glasses_per_day": round(self.glasses_per_day(), 1),
        }

def run():
    wi = WaterIntakeCalculator(weight_kg=70, climate=Climate.HOT, exercise_min=60)
    print(wi.stats())

if __name__ == "__main__":
    run()
