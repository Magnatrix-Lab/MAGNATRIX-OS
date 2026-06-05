"""Native stdlib module: Pastry Butter Calculator
Calculates lamination layers, butter ratios, and dough metrics.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PastryButterCalculator:
    dough_weight_g: float
    butter_weight_g: float
    folds: int = 3
    turns_per_fold: int = 1

    def butter_to_dough_ratio(self) -> float:
        if self.dough_weight_g == 0:
            return 0
        return self.butter_weight_g / self.dough_weight_g

    def butter_pct(self) -> float:
        total = self.dough_weight_g + self.butter_weight_g
        if total == 0:
            return 0
        return (self.butter_weight_g / total) * 100

    def total_layers(self) -> int:
        return (2 ** self.folds) ** self.turns_per_fold

    def layer_thickness_estimate_mm(self, final_pastry_thickness_mm: float = 20) -> float:
        layers = self.total_layers()
        if layers == 0:
            return 0
        return final_pastry_thickness_mm / layers

    def butter_per_layer_g(self) -> float:
        layers = self.total_layers()
        if layers == 0:
            return 0
        return self.butter_weight_g / layers

    def pastry_type(self) -> str:
        ratio = self.butter_to_dough_ratio()
        if ratio < 0.3:
            return "lean_pastry"
        elif ratio < 0.5:
            return "standard_puff"
        elif ratio < 0.7:
            return "rich_puff"
        return "extreme_puff"

    def resting_time_min_between_folds(self) -> int:
        return 20 + self.folds * 5

    def total_resting_time_min(self) -> int:
        return self.resting_time_min_between_folds() * (self.folds - 1)

    def stats(self, final_pastry_thickness_mm: float = 20) -> Dict:
        return {
            "dough_weight_g": self.dough_weight_g,
            "butter_weight_g": self.butter_weight_g,
            "butter_to_dough_ratio": round(self.butter_to_dough_ratio(), 2),
            "butter_pct": round(self.butter_pct(), 1),
            "total_layers": self.total_layers(),
            "layer_thickness_mm": round(self.layer_thickness_estimate_mm(final_pastry_thickness_mm), 4),
            "butter_per_layer_g": round(self.butter_per_layer_g(), 3),
            "pastry_type": self.pastry_type(),
            "total_resting_time_min": self.total_resting_time_min(),
        }

def run():
    pbc = PastryButterCalculator(dough_weight_g=500, butter_weight_g=375, folds=3, turns_per_fold=1)
    print(pbc.stats())

if __name__ == "__main__":
    run()
