"""Native stdlib module: Macro Calculator
Calculates macronutrient targets by goal, weight, and activity level.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class Goal(Enum):
    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"

class ActivityLevel(Enum):
    SEDENTARY = 1.2
    LIGHT = 1.375
    MODERATE = 1.55
    ACTIVE = 1.725
    VERY_ACTIVE = 1.9

@dataclass
class MacroCalculator:
    weight_kg: float
    body_fat_pct: float
    goal: Goal
    activity: ActivityLevel
    protein_per_kg: float = 2.0
    fat_pct: float = 25.0

    def bmr(self) -> float:
        return 370 + (21.6 * self.weight_kg * (1 - self.body_fat_pct / 100))

    def tdee(self) -> float:
        return self.bmr() * self.activity.value

    def target_calories(self) -> float:
        if self.goal == Goal.LOSE:
            return self.tdee() - 500
        elif self.goal == Goal.GAIN:
            return self.tdee() + 500
        return self.tdee()

    def protein_g(self) -> float:
        return self.weight_kg * self.protein_per_kg

    def fat_g(self) -> float:
        return (self.target_calories() * (self.fat_pct / 100)) / 9

    def carbs_g(self) -> float:
        protein_cals = self.protein_g() * 4
        fat_cals = self.fat_g() * 9
        remaining = self.target_calories() - protein_cals - fat_cals
        return max(0, remaining / 4)

    def stats(self) -> Dict:
        return {
            "goal": self.goal.value,
            "bmr": round(self.bmr(), 1),
            "tdee": round(self.tdee(), 1),
            "target_calories": round(self.target_calories(), 1),
            "protein_g": round(self.protein_g(), 1),
            "fat_g": round(self.fat_g(), 1),
            "carbs_g": round(self.carbs_g(), 1),
        }

def run():
    mc = MacroCalculator(weight_kg=75, body_fat_pct=15, goal=Goal.MAINTAIN, activity=ActivityLevel.MODERATE)
    print(mc.stats())

if __name__ == "__main__":
    run()
