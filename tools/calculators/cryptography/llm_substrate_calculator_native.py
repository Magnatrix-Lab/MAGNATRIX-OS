"""Native stdlib module: Substrate Calculator
Calculates mushroom substrate mix ratios, moisture content, and yield potential.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class SubstrateIngredient:
    name: str
    weight_kg: float
    moisture_pct: float
    nitrogen_pct: float

@dataclass
class SubstrateCalculator:
    mushroom_species: str
    ingredients: List[SubstrateIngredient] = field(default_factory=list)
    target_moisture_pct: float = 65.0

    def total_weight_kg(self) -> float:
        return sum(i.weight_kg for i in self.ingredients)

    def weighted_moisture_pct(self) -> float:
        if self.total_weight_kg() == 0:
            return 0.0
        total_moisture = sum(i.weight_kg * (i.moisture_pct / 100) for i in self.ingredients)
        return (total_moisture / self.total_weight_kg()) * 100

    def weighted_nitrogen_pct(self) -> float:
        if self.total_weight_kg() == 0:
            return 0.0
        total_n = sum(i.weight_kg * (i.nitrogen_pct / 100) for i in self.ingredients)
        return (total_n / self.total_weight_kg()) * 100

    def dry_weight_kg(self) -> float:
        return self.total_weight_kg() * (1 - self.weighted_moisture_pct() / 100)

    def water_to_add_l(self) -> float:
        if self.target_moisture_pct <= self.weighted_moisture_pct():
            return 0.0
        dry = self.dry_weight_kg()
        target_water = dry * (self.target_moisture_pct / (100 - self.target_moisture_pct))
        current_water = self.total_weight_kg() - dry
        return max(0, target_water - current_water)

    def yield_estimate_kg(self) -> float:
        return self.dry_weight_kg() * 0.5

    def stats(self) -> Dict:
        return {
            "species": self.mushroom_species,
            "total_weight_kg": round(self.total_weight_kg(), 1),
            "dry_weight_kg": round(self.dry_weight_kg(), 1),
            "current_moisture_pct": round(self.weighted_moisture_pct(), 1),
            "nitrogen_pct": round(self.weighted_nitrogen_pct(), 2),
            "water_to_add_l": round(self.water_to_add_l(), 1),
            "yield_estimate_kg": round(self.yield_estimate_kg(), 1),
        }

def run():
    sc = SubstrateCalculator(
        mushroom_species="Oyster",
        ingredients=[
            SubstrateIngredient("straw", 50, 12, 0.6),
            SubstrateIngredient("sawdust", 30, 8, 0.1),
            SubstrateIngredient("bran", 10, 12, 2.0),
            SubstrateIngredient("gypsum", 2, 0, 0),
        ],
        target_moisture_pct=65
    )
    print(sc.stats())

if __name__ == "__main__":
    run()
