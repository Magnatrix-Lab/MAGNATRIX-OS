"""Native stdlib module: Baker Percentage Calculator
Calculates baker's percentages, hydration, and dough formula scaling.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class BakerPercentageCalculator:
    flour_weight_g: float
    water_weight_g: float
    salt_weight_g: float
    yeast_weight_g: float
    other_ingredients: Optional[Dict[str, float]] = None

    def total_dough_weight_g(self) -> float:
        total = self.flour_weight_g + self.water_weight_g + self.salt_weight_g + self.yeast_weight_g
        if self.other_ingredients:
            total += sum(self.other_ingredients.values())
        return total

    def hydration_pct(self) -> float:
        if self.flour_weight_g == 0:
            return 0
        return (self.water_weight_g / self.flour_weight_g) * 100

    def salt_pct(self) -> float:
        if self.flour_weight_g == 0:
            return 0
        return (self.salt_weight_g / self.flour_weight_g) * 100

    def yeast_pct(self) -> float:
        if self.flour_weight_g == 0:
            return 0
        return (self.yeast_weight_g / self.flour_weight_g) * 100

    def ingredient_pcts(self) -> Dict[str, float]:
        if self.flour_weight_g == 0:
            return {}
        pcts = {
            "water": self.hydration_pct(),
            "salt": self.salt_pct(),
            "yeast": self.yeast_pct(),
        }
        if self.other_ingredients:
            for name, weight in self.other_ingredients.items():
                pcts[name] = (weight / self.flour_weight_g) * 100
        return pcts

    def scale_to_flour(self, target_flour_g: float) -> Dict[str, float]:
        if self.flour_weight_g == 0:
            return {}
        ratio = target_flour_g / self.flour_weight_g
        scaled = {
            "flour": target_flour_g,
            "water": self.water_weight_g * ratio,
            "salt": self.salt_weight_g * ratio,
            "yeast": self.yeast_weight_g * ratio,
        }
        if self.other_ingredients:
            for name, weight in self.other_ingredients.items():
                scaled[name] = weight * ratio
        return scaled

    def hydration_category(self) -> str:
        h = self.hydration_pct()
        if h < 55:
            return "stiff"
        elif h < 65:
            return "standard"
        elif h < 75:
            return "high_hydration"
        elif h < 85:
            return "very_high"
        return "extreme"

    def stats(self, target_flour_g: Optional[float] = None) -> Dict:
        result = {
            "flour_weight_g": self.flour_weight_g,
            "hydration_pct": round(self.hydration_pct(), 1),
            "salt_pct": round(self.salt_pct(), 2),
            "yeast_pct": round(self.yeast_pct(), 2),
            "ingredient_pcts": {k: round(v, 2) for k, v in self.ingredient_pcts().items()},
            "total_dough_weight_g": round(self.total_dough_weight_g(), 1),
            "hydration_category": self.hydration_category(),
        }
        if target_flour_g is not None:
            result["scaled_recipe"] = {k: round(v, 1) for k, v in self.scale_to_flour(target_flour_g).items()}
        return result

def run():
    bpc = BakerPercentageCalculator(
        flour_weight_g=1000, water_weight_g=700, salt_weight_g=20, yeast_weight_g=10,
        other_ingredients={"olive_oil": 30},
    )
    print(bpc.stats(target_flour_g=500))

if __name__ == "__main__":
    run()
