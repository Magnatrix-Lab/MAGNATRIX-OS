"""LLM Calorie Calculator — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class ActivityLevel(Enum):
    SEDENTARY = 1.2
    LIGHTLY_ACTIVE = 1.375
    MODERATELY_ACTIVE = 1.55
    VERY_ACTIVE = 1.725
    EXTREMELY_ACTIVE = 1.9

class CalorieCalculator:
    def __init__(self) -> None:
        self._activity_multipliers = {level.name: level.value for level in ActivityLevel}

    def bmr_mifflin_st_jeor(self, weight_kg: float, height_cm: float, age: int, gender: str) -> float:
        if gender.lower() == "male":
            return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    def bmr_harris_benedict(self, weight_kg: float, height_cm: float, age: int, gender: str) -> float:
        if gender.lower() == "male":
            return 88.362 + 13.397 * weight_kg + 4.799 * height_cm - 5.677 * age
        return 447.593 + 9.247 * weight_kg + 3.098 * height_cm - 4.330 * age

    def tdee(self, bmr: float, activity_level: ActivityLevel) -> float:
        return bmr * activity_level.value

    def calories_from_food(self, protein_g: float, carbs_g: float, fat_g: float) -> float:
        return protein_g * 4 + carbs_g * 4 + fat_g * 9

    def macro_split(self, total_calories: float, protein_pct: float = 0.3, carbs_pct: float = 0.4, fat_pct: float = 0.3) -> Dict[str, float]:
        return {"protein": total_calories * protein_pct / 4, "carbs": total_calories * carbs_pct / 4, "fat": total_calories * fat_pct / 9}

    def get_stats(self, weight_kg: float, height_cm: float, age: int, gender: str, activity: ActivityLevel) -> Dict[str, Any]:
        bmr = self.bmr_mifflin_st_jeor(weight_kg, height_cm, age, gender)
        tdee = self.tdee(bmr, activity)
        return {"bmr": round(bmr, 1), "tdee": round(tdee, 1), "activity": activity.name}

def run() -> None:
    print("Calorie Calculator test")
    e = CalorieCalculator()
    print("  Male 70kg 175cm 30y moderate: " + str(e.get_stats(70, 175, 30, "male", ActivityLevel.MODERATELY_ACTIVE)))
    print("  Female 55kg 160cm 25y lightly: " + str(e.get_stats(55, 160, 25, "female", ActivityLevel.LIGHTLY_ACTIVE)))
    print("  Food calories: " + str(e.calories_from_food(100, 200, 50)))
    print("  Macro split 2000 cal: " + str(e.macro_split(2000)))
    print("Calorie Calculator test complete.")

if __name__ == "__main__":
    run()
