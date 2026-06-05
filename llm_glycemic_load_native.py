"""Native stdlib module: Glycemic Load Calculator
Calculates glycemic load and insulin index for meals.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class FoodItem:
    name: str
    carbs_g: float
    gi: float
    serving_g: float

@dataclass
class GlycemicLoadCalculator:
    meal_name: str
    foods: List[FoodItem] = field(default_factory=list)

    def glycemic_load(self, food: FoodItem) -> float:
        if food.serving_g == 0:
            return 0.0
        carbs_per_serving = (food.carbs_g / 100) * food.serving_g
        return (carbs_per_serving * food.gi) / 100

    def total_gl(self) -> float:
        return sum(self.glycemic_load(f) for f in self.foods)

    def total_carbs_g(self) -> float:
        return sum((f.carbs_g / 100) * f.serving_g for f in self.foods)

    def avg_gi(self) -> float:
        if self.total_carbs_g() == 0:
            return 0.0
        weighted = sum(f.gi * (f.carbs_g / 100) * f.serving_g for f in self.foods)
        return weighted / self.total_carbs_g()

    def classification(self) -> str:
        gl = self.total_gl()
        if gl <= 10:
            return "low"
        elif gl <= 20:
            return "medium"
        return "high"

    def stats(self) -> Dict:
        return {
            "meal": self.meal_name,
            "total_glycemic_load": round(self.total_gl(), 1),
            "total_carbs_g": round(self.total_carbs_g(), 1),
            "avg_gi": round(self.avg_gi(), 1),
            "classification": self.classification(),
        }

def run():
    glc = GlycemicLoadCalculator(
        meal_name="Breakfast Bowl",
        foods=[
            FoodItem("oats", 66, 55, 40),
            FoodItem("banana", 23, 51, 100),
            FoodItem("milk", 5, 31, 200),
            FoodItem("honey", 82, 58, 15),
        ]
    )
    print(glc.stats())

if __name__ == "__main__":
    run()
