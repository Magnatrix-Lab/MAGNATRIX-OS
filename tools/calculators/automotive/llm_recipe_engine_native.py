"""Recipe Engine — scaling, substitutions, cost, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Ingredient:
    name: str
    amount: float
    unit: str
    cost_per_unit: float = 0.0

class RecipeEngine:
    def __init__(self):
        self.ingredients: List[Ingredient] = []
        self.servings: int = 1

    def add_ingredient(self, i: Ingredient):
        self.ingredients.append(i)

    def scale(self, new_servings: int) -> List[Ingredient]:
        factor = new_servings / self.servings if self.servings > 0 else 1
        return [Ingredient(i.name, i.amount * factor, i.unit, i.cost_per_unit) for i in self.ingredients]

    def substitute(self, ingredient: str, alt: str, amount: float) -> List[Ingredient]:
        result = []
        for i in self.ingredients:
            if i.name == ingredient:
                result.append(Ingredient(alt, amount, i.unit, i.cost_per_unit))
            else:
                result.append(Ingredient(i.name, i.amount, i.unit, i.cost_per_unit))
        return result

    def total_cost(self) -> float:
        return sum(i.amount * i.cost_per_unit for i in self.ingredients)

    def cost_per_serving(self) -> float:
        return self.total_cost() / self.servings if self.servings > 0 else 0.0

    def stats(self) -> Dict:
        return {"ingredients": len(self.ingredients), "cost": round(self.total_cost(), 2), "per_serving": round(self.cost_per_serving(), 2)}

def run():
    re = RecipeEngine()
    re.servings = 4
    re.add_ingredient(Ingredient("flour", 500, "g", 0.002))
    re.add_ingredient(Ingredient("sugar", 100, "g", 0.005))
    re.add_ingredient(Ingredient("eggs", 2, "pc", 0.3))
    print(re.stats())
    print("Scaled for 8:", [(i.name, i.amount) for i in re.scale(8)])

if __name__ == "__main__":
    run()
