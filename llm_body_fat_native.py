"""Native stdlib module: Body Fat Calculator
Estimates body fat percentage using Navy and BMI-based methods.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class Gender(Enum):
    MALE = "male"
    FEMALE = "female"

@dataclass
class BodyFatCalculator:
    gender: Gender
    height_cm: float
    weight_kg: float
    waist_cm: float
    neck_cm: float = 0.0
    hip_cm: float = 0.0

    def bmi(self) -> float:
        if self.height_cm == 0:
            return 0.0
        return self.weight_kg / ((self.height_cm / 100) ** 2)

    def navy_method_pct(self) -> float:
        if self.waist_cm == 0 or self.neck_cm == 0:
            return 0.0
        h = self.height_cm
        if self.gender == Gender.MALE:
            return 495 / (1.0324 - 0.19077 * (self.waist_cm - self.neck_cm) / h + 0.15456 * (h / 100)) - 450
        else:
            if self.hip_cm == 0:
                return 0.0
            return 495 / (1.29579 - 0.35004 * (self.waist_cm + self.hip_cm - self.neck_cm) / h + 0.22100 * (h / 100)) - 450

    def bmi_method_pct(self) -> float:
        if self.gender == Gender.MALE:
            return (1.20 * self.bmi()) + (0.23 * 30) - (10.8 * 1) - 5.4
        else:
            return (1.20 * self.bmi()) + (0.23 * 30) - (10.8 * 0) - 5.4

    def lean_mass_kg(self) -> float:
        return self.weight_kg * (1 - self.navy_method_pct() / 100)

    def stats(self) -> Dict:
        return {
            "bmi": round(self.bmi(), 1),
            "navy_body_fat_pct": round(self.navy_method_pct(), 1),
            "bmi_body_fat_pct": round(self.bmi_method_pct(), 1),
            "lean_mass_kg": round(self.lean_mass_kg(), 1),
        }

def run():
    bf = BodyFatCalculator(gender=Gender.MALE, height_cm=180, weight_kg=80, waist_cm=85, neck_cm=38, hip_cm=0)
    print(bf.stats())

if __name__ == "__main__":
    run()
