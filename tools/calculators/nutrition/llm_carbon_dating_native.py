"""Native stdlib module: Carbon Dating Calculator
Calculates radiocarbon dates, calibration ranges, and confidence intervals.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class CarbonDatingCalculator:
    sample_name: str
    c14_age_bp: float
    c14_error: float
    calibration_curve: str = "intcal20"

    def calibrated_age_range(self) -> tuple:
        lower = self.c14_age_bp - (2 * self.c14_error)
        upper = self.c14_age_bp + (2 * self.c14_error)
        return (max(0, lower), upper)

    def calibrated_age_mid(self) -> float:
        return self.c14_age_bp

    def half_life_remaining(self) -> float:
        half_life = 5730
        if self.c14_age_bp <= 0:
            return 100.0
        return (0.5 ** (self.c14_age_bp / half_life)) * 100

    def decay_constant(self) -> float:
        return math.log(2) / 5730

    def modern_carbon_fraction(self) -> float:
        return 0.5 ** (self.c14_age_bp / 5730)

    def stats(self) -> Dict:
        return {
            "sample": self.sample_name,
            "c14_age_bp": self.c14_age_bp,
            "error": self.c14_error,
            "calibrated_2sigma": self.calibrated_age_range(),
            "half_life_remaining_pct": round(self.half_life_remaining(), 6),
            "modern_carbon_fraction": round(self.modern_carbon_fraction(), 6),
        }

def run():
    cdc = CarbonDatingCalculator(sample_name="Bone-42", c14_age_bp=3250, c14_error=35, calibration_curve="intcal20")
    print(cdc.stats())

if __name__ == "__main__":
    run()
