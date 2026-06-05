"""Native stdlib module: Coral Health Calculator
Calculates coral bleaching risk, growth rates, and coverage metrics.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class CoralType(Enum):
    BRANCHING = "branching"
    MASSIVE = "massive"
    PLATE = "plate"
    ENCRUSTING = "encrusting"
    FOLIOSE = "foliose"

@dataclass
class CoralHealthCalculator:
    coral_type: CoralType
    coverage_pct: float
    bleaching_index: float
    water_temperature_c: float
    ph: float
    depth_m: float

    def growth_rate_mm_per_year(self) -> float:
        rates = {CoralType.BRANCHING: 100, CoralType.PLATE: 80, CoralType.FOLIOSE: 60, CoralType.MASSIVE: 10, CoralType.ENCRUSTING: 5}
        base = rates.get(self.coral_type, 50)
        if self.water_temperature_c > 29:
            base *= 0.7
        if self.ph < 7.8:
            base *= 0.8
        return base

    def bleaching_risk(self) -> str:
        if self.water_temperature_c > 30 and self.bleaching_index > 3:
            return "severe"
        elif self.water_temperature_c > 29 or self.bleaching_index > 2:
            return "moderate"
        elif self.water_temperature_c > 28:
            return "low"
        return "minimal"

    def calcification_rate_g_cm2_yr(self) -> float:
        base = 1.5
        if self.ph < 8.0:
            base *= (self.ph - 7.5) / 0.5
        if self.water_temperature_c < 25 or self.water_temperature_c > 30:
            base *= 0.8
        return max(0, base)

    def years_to_recovery(self, target_coverage_pct: float = 80) -> float:
        if self.growth_rate_mm_per_year() == 0:
            return 0.0
        gap = max(0, target_coverage_pct - self.coverage_pct)
        return gap / (self.growth_rate_mm_per_year() / 10)

    def stats(self) -> Dict:
        return {
            "coral_type": self.coral_type.value,
            "coverage_pct": self.coverage_pct,
            "growth_rate_mm_yr": round(self.growth_rate_mm_per_year(), 1),
            "bleaching_risk": self.bleaching_risk(),
            "calcification_g_cm2_yr": round(self.calcification_rate_g_cm2_yr(), 2),
            "years_to_recovery": round(self.years_to_recovery(), 1),
        }

def run():
    chc = CoralHealthCalculator(coral_type=CoralType.BRANCHING, coverage_pct=45, bleaching_index=2.5, water_temperature_c=28.5, ph=7.9, depth_m=8)
    print(chc.stats())

if __name__ == "__main__":
    run()
