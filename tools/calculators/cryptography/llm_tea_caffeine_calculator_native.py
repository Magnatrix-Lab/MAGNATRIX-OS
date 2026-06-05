"""Native stdlib module: Tea Caffeine Calculator
Estimates caffeine content, extraction rates, and total intake.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class TeaCaffeineCalculator:
    tea_type: str
    leaf_weight_g: float
    steep_time_min: float = 3.0
    water_temp_c: float = 90.0
    infusions: int = 1

    _CAFFEINE_MG_PER_G = {
        "green": 25, "white": 20, "oolong": 30, "black": 40, "puerh": 35, "herbal": 0, "matcha": 35,
    }

    def total_caffeine_mg(self) -> float:
        return self.leaf_weight_g * self._CAFFEINE_MG_PER_G.get(self.tea_type, 25)

    def extraction_rate_pct(self) -> float:
        base = 60
        time_bonus = min(30, self.steep_time_min * 5)
        temp_bonus = max(-10, (self.water_temp_c - 80) * 1)
        return base + time_bonus + temp_bonus

    def caffeine_extracted_mg(self) -> float:
        return self.total_caffeine_mg() * (self.extraction_rate_pct() / 100)

    def caffeine_per_infusion_mg(self) -> float:
        if self.infusions == 0:
            return 0
        return self.caffeine_extracted_mg() / self.infusions

    def caffeine_per_cup_mg(self) -> float:
        return self.caffeine_extracted_mg()

    def caffeine_category(self) -> str:
        mg = self.caffeine_per_cup_mg()
        if mg < 20:
            return "low"
        elif mg < 50:
            return "moderate"
        elif mg < 80:
            return "high"
        return "very_high"

    def daily_intake_pct_of_limit(self, daily_limit_mg: float = 400) -> float:
        if daily_limit_mg == 0:
            return 0
        return (self.caffeine_per_cup_mg() / daily_limit_mg) * 100

    def stats(self, daily_limit_mg: float = 400) -> Dict:
        return {
            "tea_type": self.tea_type,
            "leaf_weight_g": self.leaf_weight_g,
            "total_caffeine_mg": round(self.total_caffeine_mg(), 1),
            "extraction_rate_pct": round(self.extraction_rate_pct(), 1),
            "caffeine_extracted_mg": round(self.caffeine_extracted_mg(), 1),
            "caffeine_per_cup_mg": round(self.caffeine_per_cup_mg(), 1),
            "caffeine_category": self.caffeine_category(),
            "daily_intake_pct_of_limit": round(self.daily_intake_pct_of_limit(daily_limit_mg), 1),
        }

def run():
    tcc = TeaCaffeineCalculator(tea_type="black", leaf_weight_g=3, steep_time_min=4, water_temp_c=95, infusions=1)
    print(tcc.stats())

if __name__ == "__main__":
    run()
