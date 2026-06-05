"""Native stdlib module: Barrel Aging Calculator
Calculates angel's share, oak extraction, and aging time.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class BarrelAgingCalculator:
    barrel_volume_l: float
    fill_volume_l: float
    initial_abv_pct: float
    climate: str = "temperate"  # temperate, hot, cold, humid
    aging_years: float = 3.0

    _ANGELS_SHARE_PCT_PER_YEAR = {
        "temperate": 2, "hot": 4, "cold": 1, "humid": 1.5,
    }

    def angels_share_pct(self) -> float:
        rate = self._ANGELS_SHARE_PCT_PER_YEAR.get(self.climate, 2)
        return rate * self.aging_years

    def volume_loss_l(self) -> float:
        return self.fill_volume_l * (self.angels_share_pct() / 100)

    def remaining_volume_l(self) -> float:
        return self.fill_volume_l - self.volume_loss_l()

    def abv_increase_pct(self) -> float:
        if self.climate in ["hot", "temperate"]:
            return self.aging_years * 0.5
        return self.aging_years * 0.2

    def final_abv_pct(self) -> float:
        return self.initial_abv_pct + self.abv_increase_pct()

    def oak_extraction_score(self) -> float:
        base = min(100, self.aging_years * 20)
        if self.climate == "hot":
            base *= 1.2
        elif self.climate == "cold":
            base *= 0.8
        return min(100, base)

    def color_intensity_estimate(self) -> str:
        score = self.oak_extraction_score()
        if score < 20:
            return "very_pale"
        elif score < 40:
            return "pale"
        elif score < 60:
            return "light_amber"
        elif score < 80:
            return "amber"
        return "dark_amber"

    def stats(self) -> Dict:
        return {
            "barrel_volume_l": self.barrel_volume_l,
            "fill_volume_l": self.fill_volume_l,
            "aging_years": self.aging_years,
            "climate": self.climate,
            "angels_share_pct": round(self.angels_share_pct(), 1),
            "volume_loss_l": round(self.volume_loss_l(), 2),
            "remaining_volume_l": round(self.remaining_volume_l(), 2),
            "final_abv_pct": round(self.final_abv_pct(), 1),
            "oak_extraction_score": round(self.oak_extraction_score(), 1),
            "color_intensity": self.color_intensity_estimate(),
        }

def run():
    bac = BarrelAgingCalculator(barrel_volume_l=200, fill_volume_l=190, initial_abv_pct=62, climate="hot", aging_years=5)
    print(bac.stats())

if __name__ == "__main__":
    run()
