"""Native stdlib module: Perfume Dilution Calculator
Calculates dilution ratios, concentration levels, and alcohol percentages.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PerfumeDilutionCalculator:
    concentrate_volume_ml: float
    concentrate_cost_per_ml: float
    desired_concentration_pct: float  # e.g., 15 for eau de parfum
    alcohol_volume_ml: float = 0.0

    def total_batch_volume_ml(self) -> float:
        if self.desired_concentration_pct == 0:
            return 0
        return self.concentrate_volume_ml / (self.desired_concentration_pct / 100)

    def alcohol_needed_ml(self) -> float:
        return self.total_batch_volume_ml() - self.concentrate_volume_ml

    def alcohol_pct(self) -> float:
        if self.total_batch_volume_ml() == 0:
            return 0
        return (self.alcohol_needed_ml() / self.total_batch_volume_ml()) * 100

    def cost_per_ml(self) -> float:
        if self.total_batch_volume_ml() == 0:
            return 0
        return (self.concentrate_volume_ml * self.concentrate_cost_per_ml) / self.total_batch_volume_ml()

    def concentration_category(self) -> str:
        if self.desired_concentration_pct >= 20:
            return "parfum"
        elif self.desired_concentration_pct >= 15:
            return "eau_de_parfum"
        elif self.desired_concentration_pct >= 10:
            return "eau_de_toilette"
        elif self.desired_concentration_pct >= 5:
            return "eau_de_cologne"
        return "eau_fraiche"

    def recommended_maceration_weeks(self) -> int:
        conc = self.desired_concentration_pct
        if conc >= 20:
            return 6
        elif conc >= 15:
            return 4
        elif conc >= 10:
            return 3
        return 2

    def stats(self) -> Dict:
        return {
            "concentrate_volume_ml": self.concentrate_volume_ml,
            "desired_concentration_pct": self.desired_concentration_pct,
            "concentration_category": self.concentration_category(),
            "total_batch_volume_ml": round(self.total_batch_volume_ml(), 1),
            "alcohol_needed_ml": round(self.alcohol_needed_ml(), 1),
            "alcohol_pct": round(self.alcohol_pct(), 1),
            "cost_per_ml": round(self.cost_per_ml(), 2),
            "maceration_weeks": self.recommended_maceration_weeks(),
        }

def run():
    pdc = PerfumeDilutionCalculator(concentrate_volume_ml=30, concentrate_cost_per_ml=2.5, desired_concentration_pct=15)
    print(pdc.stats())

if __name__ == "__main__":
    run()
