"""Nutrition Calculator — macros, calories, BMI, BMR, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class NutritionCalculator:
    weight_kg: float = 70.0
    height_cm: float = 175.0
    age: int = 30
    gender: str = "male"
    activity_level: float = 1.2

    def bmi(self) -> float:
        h = self.height_cm / 100
        return self.weight_kg / (h * h) if h > 0 else 0.0

    def bmr_mifflin(self) -> float:
        bmr = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age
        if self.gender == "male":
            bmr += 5
        else:
            bmr -= 161
        return bmr

    def tdee(self) -> float:
        return self.bmr_mifflin() * self.activity_level

    def macros(self, calories: float, protein_pct: float = 0.3, fat_pct: float = 0.3, carb_pct: float = 0.4) -> Dict:
        return {
            "protein_g": calories * protein_pct / 4,
            "fat_g": calories * fat_pct / 9,
            "carbs_g": calories * carb_pct / 4,
        }

    def bmi_category(self) -> str:
        b = self.bmi()
        if b < 18.5: return "underweight"
        elif b < 25: return "normal"
        elif b < 30: return "overweight"
        return "obese"

    def stats(self) -> Dict:
        return {"bmi": round(self.bmi(), 1), "bmr": round(self.bmr_mifflin(), 0), "tdee": round(self.tdee(), 0), "category": self.bmi_category()}

def run():
    nc = NutritionCalculator(weight_kg=80, height_cm=180, age=35, activity_level=1.55)
    print(nc.stats())
    print("Macros:", nc.macros(nc.tdee()))

if __name__ == "__main__":
    run()
