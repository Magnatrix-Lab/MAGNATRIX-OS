"""Native stdlib module: Compost Calculator
Calculates C:N ratio, moisture, and turning schedule for composting.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class CompostIngredient:
    name: str
    weight_kg: float
    carbon_pct: float
    nitrogen_pct: float
    moisture_pct: float

@dataclass
class CompostCalculator:
    pile_name: str
    ingredients: List[CompostIngredient] = field(default_factory=list)
    target_moisture_pct: float = 60.0

    def total_weight_kg(self) -> float:
        return sum(i.weight_kg for i in self.ingredients)

    def total_carbon_kg(self) -> float:
        return sum(i.weight_kg * (i.carbon_pct / 100) for i in self.ingredients)

    def total_nitrogen_kg(self) -> float:
        return sum(i.weight_kg * (i.nitrogen_pct / 100) for i in self.ingredients)

    def cn_ratio(self) -> float:
        if self.total_nitrogen_kg() == 0:
            return 0.0
        return self.total_carbon_kg() / self.total_nitrogen_kg()

    def weighted_moisture_pct(self) -> float:
        if self.total_weight_kg() == 0:
            return 0.0
        total_water = sum(i.weight_kg * (i.moisture_pct / 100) for i in self.ingredients)
        return (total_water / self.total_weight_kg()) * 100

    def water_to_add_l(self) -> float:
        if self.target_moisture_pct <= self.weighted_moisture_pct():
            return 0.0
        dry = self.total_weight_kg() * (1 - self.weighted_moisture_pct() / 100)
        target_water = dry * (self.target_moisture_pct / (100 - self.target_moisture_pct))
        current_water = self.total_weight_kg() - dry
        return max(0, target_water - current_water)

    def cn_status(self) -> str:
        cn = self.cn_ratio()
        if 25 <= cn <= 35:
            return "optimal"
        elif cn < 20:
            return "too_low_add_browns"
        elif cn > 40:
            return "too_high_add_greens"
        return "acceptable"

    def stats(self) -> Dict:
        return {
            "pile": self.pile_name,
            "total_weight_kg": round(self.total_weight_kg(), 1),
            "cn_ratio": round(self.cn_ratio(), 1),
            "cn_status": self.cn_status(),
            "moisture_pct": round(self.weighted_moisture_pct(), 1),
            "water_to_add_l": round(self.water_to_add_l(), 1),
        }

def run():
    cc = CompostCalculator(
        pile_name="Backyard Compost",
        ingredients=[
            CompostIngredient("leaves", 50, 50, 1, 40),
            CompostIngredient("grass_clippings", 30, 15, 3, 70),
            CompostIngredient("food_scraps", 20, 15, 2, 80),
            CompostIngredient("coffee_grounds", 10, 20, 2, 60),
        ]
    )
    print(cc.stats())

if __name__ == "__main__":
    run()
