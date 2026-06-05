"""Native stdlib module: Ganache Ratio Calculator
Calculates chocolate:cream ratios, consistency, and shelf life.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class GanacheRatioCalculator:
    chocolate_weight_g: float
    cream_weight_g: float
    chocolate_type: str = "dark"  # dark, milk, white
    desired_use: str = "filling"  # filling, truffle, glaze, coating

    def ratio_chocolate_to_cream(self) -> float:
        if self.cream_weight_g == 0:
            return 0
        return self.chocolate_weight_g / self.cream_weight_g

    def ratio_chocolate_pct(self) -> float:
        total = self.chocolate_weight_g + self.cream_weight_g
        if total == 0:
            return 0
        return (self.chocolate_weight_g / total) * 100

    def consistency(self) -> str:
        ratio = self.ratio_chocolate_to_cream()
        if ratio < 1.0:
            return "soft"
        elif ratio < 1.5:
            return "medium"
        elif ratio < 2.0:
            return "firm"
        return "very_firm"

    def shelf_life_days(self) -> int:
        base = 14
        if self.chocolate_type == "white":
            base = 7
        elif self.chocolate_type == "milk":
            base = 10
        if self.ratio_chocolate_to_cream() > 1.5:
            base += 7
        return base

    def recommended_ratio(self) -> float:
        ratios = {"filling": 1.5, "truffle": 2.0, "glaze": 1.0, "coating": 2.5}
        return ratios.get(self.desired_use, 1.5)

    def ratio_match_score(self) -> float:
        recommended = self.recommended_ratio()
        actual = self.ratio_chocolate_to_cream()
        if recommended == 0:
            return 0
        diff = abs(actual - recommended) / recommended
        return max(0, 100 - diff * 100)

    def butter_needed_g(self) -> float:
        return (self.chocolate_weight_g + self.cream_weight_g) * 0.05

    def stats(self) -> Dict:
        return {
            "chocolate_weight_g": self.chocolate_weight_g,
            "cream_weight_g": self.cream_weight_g,
            "ratio_chocolate_to_cream": round(self.ratio_chocolate_to_cream(), 2),
            "chocolate_pct": round(self.ratio_chocolate_pct(), 1),
            "consistency": self.consistency(),
            "shelf_life_days": self.shelf_life_days(),
            "recommended_ratio": self.recommended_ratio(),
            "ratio_match_score": round(self.ratio_match_score(), 1),
            "butter_needed_g": round(self.butter_needed_g(), 1),
        }

def run():
    grc = GanacheRatioCalculator(chocolate_weight_g=300, cream_weight_g=150, chocolate_type="dark", desired_use="truffle")
    print(grc.stats())

if __name__ == "__main__":
    run()
