"""Native stdlib module: Meal Planner
Plans daily meals by calorie targets and macronutrient ratios.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Meal:
    name: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float

@dataclass
class MealPlanner:
    target_calories: float
    target_protein_g: float
    target_carbs_g: float
    target_fat_g: float
    meals: List[Meal] = field(default_factory=list)

    def total_calories(self) -> float:
        return sum(m.calories for m in self.meals)

    def total_protein(self) -> float:
        return sum(m.protein_g for m in self.meals)

    def total_carbs(self) -> float:
        return sum(m.carbs_g for m in self.meals)

    def total_fat(self) -> float:
        return sum(m.fat_g for m in self.meals)

    def calorie_variance_pct(self) -> float:
        if self.target_calories == 0:
            return 0.0
        return ((self.total_calories() - self.target_calories) / self.target_calories) * 100

    def on_target(self, tolerance_pct: float = 10) -> bool:
        return abs(self.calorie_variance_pct()) <= tolerance_pct

    def stats(self) -> Dict:
        return {
            "target_calories": self.target_calories,
            "actual_calories": round(self.total_calories(), 1),
            "actual_protein_g": round(self.total_protein(), 1),
            "actual_carbs_g": round(self.total_carbs(), 1),
            "actual_fat_g": round(self.total_fat(), 1),
            "variance_pct": round(self.calorie_variance_pct(), 1),
            "on_target": self.on_target(),
        }

def run():
    mp = MealPlanner(
        target_calories=2200,
        target_protein_g=150,
        target_carbs_g=250,
        target_fat_g=70,
        meals=[
            Meal("Breakfast", 550, 35, 60, 18),
            Meal("Lunch", 700, 45, 75, 22),
            Meal("Snack", 300, 15, 35, 10),
            Meal("Dinner", 650, 50, 70, 20),
        ]
    )
    print(mp.stats())

if __name__ == "__main__":
    run()
