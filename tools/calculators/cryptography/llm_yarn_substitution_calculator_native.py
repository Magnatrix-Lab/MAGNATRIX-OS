"""Native stdlib module: Yarn Substitution Calculator
Converts yardage, weight, and twist between different yarn specifications.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class YarnSubstitutionCalculator:
    original_yarn_meters_per_50g: float
    substitute_yarn_meters_per_50g: float
    pattern_yardage_m: float
    original_gauge_sts_per_10cm: float
    substitute_gauge_sts_per_10cm: float

    def substitute_yardage_m(self) -> float:
        if self.original_yarn_meters_per_50g == 0:
            return 0
        return self.pattern_yardage_m * (self.substitute_yarn_meters_per_50g / self.original_yarn_meters_per_50g)

    def original_balls_needed(self, ball_weight_g: float = 50.0) -> int:
        if self.original_yarn_meters_per_50g == 0:
            return 0
        return math.ceil(self.pattern_yardage_m / (self.original_yarn_meters_per_50g * (ball_weight_g / 50)))

    def substitute_balls_needed(self, ball_weight_g: float = 50.0) -> int:
        if self.substitute_yarn_meters_per_50g == 0:
            return 0
        return math.ceil(self.substitute_yardage_m() / (self.substitute_yarn_meters_per_50g * (ball_weight_g / 50)))

    def gauge_difference_pct(self) -> float:
        if self.original_gauge_sts_per_10cm == 0:
            return 0
        return ((self.substitute_gauge_sts_per_10cm - self.original_gauge_sts_per_10cm) / self.original_gauge_sts_per_10cm) * 100

    def fabric_drape_change(self) -> str:
        diff = self.gauge_difference_pct()
        if diff < -10:
            return "looser_drape"
        elif diff > 10:
            return "denser_fabric"
        return "similar_drape"

    def recommended_needle_change(self) -> str:
        diff = self.gauge_difference_pct()
        if diff < -15:
            return "decrease_needle_size"
        elif diff > 15:
            return "increase_needle_size"
        return "same_needle_size"

    def stats(self, ball_weight_g: float = 50.0) -> Dict:
        return {
            "substitute_yardage_m": round(self.substitute_yardage_m(), 1),
            "original_balls_needed": self.original_balls_needed(ball_weight_g),
            "substitute_balls_needed": self.substitute_balls_needed(ball_weight_g),
            "gauge_difference_pct": round(self.gauge_difference_pct(), 1),
            "fabric_drape_change": self.fabric_drape_change(),
            "recommended_needle_change": self.recommended_needle_change(),
        }

def run():
    ysc = YarnSubstitutionCalculator(
        original_yarn_meters_per_50g=175, substitute_yarn_meters_per_50g=200,
        pattern_yardage_m=800, original_gauge_sts_per_10cm=20, substitute_gauge_sts_per_10cm=22,
    )
    print(ysc.stats())

if __name__ == "__main__":
    run()
