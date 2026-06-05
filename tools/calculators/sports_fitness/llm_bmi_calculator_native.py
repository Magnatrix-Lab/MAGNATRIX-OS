"""Native stdlib module: BMI Calculator
Calculates BMI, BMI category, and ideal weight range.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class BMICategory(Enum):
    UNDERWEIGHT = "underweight"
    NORMAL = "normal"
    OVERWEIGHT = "overweight"
    OBESE_1 = "obese_class_1"
    OBESE_2 = "obese_class_2"
    OBESE_3 = "obese_class_3"

@dataclass
class BMICalculator:
    height_m: float
    weight_kg: float

    def bmi(self) -> float:
        if self.height_m == 0:
            return 0.0
        return self.weight_kg / (self.height_m ** 2)

    def category(self) -> BMICategory:
        b = self.bmi()
        if b < 18.5:
            return BMICategory.UNDERWEIGHT
        elif b < 25:
            return BMICategory.NORMAL
        elif b < 30:
            return BMICategory.OVERWEIGHT
        elif b < 35:
            return BMICategory.OBESE_1
        elif b < 40:
            return BMICategory.OBESE_2
        return BMICategory.OBESE_3

    def ideal_weight_range_kg(self) -> tuple:
        min_w = 18.5 * (self.height_m ** 2)
        max_w = 24.9 * (self.height_m ** 2)
        return (round(min_w, 1), round(max_w, 1))

    def weight_to_lose_kg(self) -> float:
        max_ideal = self.ideal_weight_range_kg()[1]
        if self.weight_kg > max_ideal:
            return self.weight_kg - max_ideal
        return 0.0

    def stats(self) -> Dict:
        return {
            "bmi": round(self.bmi(), 1),
            "category": self.category().value,
            "ideal_weight_range_kg": self.ideal_weight_range_kg(),
            "weight_to_lose_kg": round(self.weight_to_lose_kg(), 1),
        }

def run():
    bmi = BMICalculator(height_m=1.75, weight_kg=82)
    print(bmi.stats())

if __name__ == "__main__":
    run()
