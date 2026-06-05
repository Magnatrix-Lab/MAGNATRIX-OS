"""Native stdlib module: Distillation Yield Calculator
Calculates wash ABV, spirit yield, and cut points for distillation.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class DistillationYieldCalculator:
    wash_volume_l: float
    wash_abv_pct: float
    still_efficiency_pct: float = 75.0
    target_abv_pct: float = 40.0

    def total_alcohol_ml(self) -> float:
        return self.wash_volume_l * 1000 * (self.wash_abv_pct / 100)

    def recovered_alcohol_ml(self) -> float:
        return self.total_alcohol_ml() * (self.still_efficiency_pct / 100)

    def spirit_yield_l(self) -> float:
        if self.target_abv_pct == 0:
            return 0
        return self.recovered_alcohol_ml() / 1000 / (self.target_abv_pct / 100)

    def heads_pct(self) -> float:
        return 5.0

    def hearts_pct(self) -> float:
        return 70.0

    def tails_pct(self) -> float:
        return 25.0

    def heads_volume_l(self) -> float:
        return self.spirit_yield_l() * (self.heads_pct() / 100)

    def hearts_volume_l(self) -> float:
        return self.spirit_yield_l() * (self.hearts_pct() / 100)

    def tails_volume_l(self) -> float:
        return self.spirit_yield_l() * (self.tails_pct() / 100)

    def yield_per_kg_fermentable(self, kg_fermentable: float) -> float:
        if kg_fermentable == 0:
            return 0
        return self.spirit_yield_l() / kg_fermentable

    def stats(self, kg_fermentable: Optional[float] = None) -> Dict:
        result = {
            "wash_volume_l": self.wash_volume_l,
            "wash_abv_pct": self.wash_abv_pct,
            "total_alcohol_ml": round(self.total_alcohol_ml(), 1),
            "recovered_alcohol_ml": round(self.recovered_alcohol_ml(), 1),
            "spirit_yield_l": round(self.spirit_yield_l(), 2),
            "heads_volume_l": round(self.heads_volume_l(), 2),
            "hearts_volume_l": round(self.hearts_volume_l(), 2),
            "tails_volume_l": round(self.tails_volume_l(), 2),
        }
        if kg_fermentable is not None:
            result["yield_per_kg_fermentable_l"] = round(self.yield_per_kg_fermentable(kg_fermentable), 2)
        return result

def run():
    dyc = DistillationYieldCalculator(wash_volume_l=50, wash_abv_pct=8, still_efficiency_pct=80, target_abv_pct=40)
    print(dyc.stats(kg_fermentable=10))

if __name__ == "__main__":
    run()
