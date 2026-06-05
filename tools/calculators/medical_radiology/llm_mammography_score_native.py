"""Native stdlib module: Mammography Score Calculator
Calculates breast density, BI-RADS scores, and cancer risk estimates.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class BreastDensity(Enum):
    A = "a"  # Fatty
    B = "b"  # Scattered
    C = "c"  # Heterogeneous
    D = "d"  # Dense

@dataclass
class MammographyScoreCalculator:
    breast_density: BreastDensity
    age: int
    family_history: bool
    prior_biopsy: bool
    bmi: float

    def density_risk_multiplier(self) -> float:
        multipliers = {BreastDensity.A: 1.0, BreastDensity.B: 1.2, BreastDensity.C: 1.5, BreastDensity.D: 2.0}
        return multipliers.get(self.breast_density, 1.0)

    def birads_score(self) -> int:
        score = 0
        if self.breast_density in [BreastDensity.C, BreastDensity.D]:
            score += 1
        if self.age >= 50:
            score += 1
        if self.family_history:
            score += 2
        if self.prior_biopsy:
            score += 1
        if self.bmi > 30:
            score += 1
        return min(6, score)

    def birads_category(self) -> str:
        s = self.birads_score()
        if s <= 1:
            return "BI-RADS 1: Negative"
        elif s == 2:
            return "BI-RADS 2: Benign"
        elif s == 3:
            return "BI-RADS 3: Probably benign"
        elif s == 4:
            return "BI-RADS 4: Suspicious"
        elif s == 5:
            return "BI-RADS 5: Highly suggestive of malignancy"
        return "BI-RADS 6: Known biopsy-proven malignancy"

    def lifetime_risk_pct(self) -> float:
        base = 12.0
        return base * self.density_risk_multiplier()

    def recommended_screening_interval_months(self) -> int:
        if self.birads_score() >= 4:
            return 6
        elif self.breast_density == BreastDensity.D:
            return 12
        return 24

    def stats(self) -> Dict:
        return {
            "density": self.breast_density.value.upper(),
            "birads_score": self.birads_score(),
            "birads_category": self.birads_category(),
            "lifetime_risk_pct": round(self.lifetime_risk_pct(), 1),
            "screening_interval_months": self.recommended_screening_interval_months(),
        }

def run():
    msc = MammographyScoreCalculator(breast_density=BreastDensity.C, age=45, family_history=True, prior_biopsy=False, bmi=28)
    print(msc.stats())

if __name__ == "__main__":
    run()
