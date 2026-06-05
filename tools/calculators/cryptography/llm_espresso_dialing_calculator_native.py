"""Native stdlib module: Espresso Dialing Calculator
Calculates shot time, yield, and extraction ratios for espresso.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class EspressoDialingCalculator:
    dose_g: float
    yield_g: float
    shot_time_s: float
    target_time_s: float = 30.0

    def ratio(self) -> float:
        if self.dose_g == 0:
            return 0
        return self.yield_g / self.dose_g

    def flow_rate_g_per_s(self) -> float:
        if self.shot_time_s == 0:
            return 0
        return self.yield_g / self.shot_time_s

    def time_difference_s(self) -> float:
        return self.shot_time_s - self.target_time_s

    def time_deviation_pct(self) -> float:
        if self.target_time_s == 0:
            return 0
        return (self.time_difference_s() / self.target_time_s) * 100

    def grind_recommendation(self) -> str:
        diff = self.time_difference_s()
        if diff < -5:
            return "coarsen_grind"
        elif diff < -2:
            return "coarsen_slightly"
        elif diff < 2:
            return "grind_is_good"
        elif diff < 5:
            return "fine_slightly"
        return "fine_grind"

    def dose_recommendation(self) -> str:
        ratio = self.ratio()
        if ratio < 1.5:
            return "ratio_too_low_increase_yield_or_reduce_dose"
        elif ratio > 3.5:
            return "ratio_too_high_reduce_yield_or_increase_dose"
        return "ratio_good"

    def estimated_tds_pct(self) -> float:
        ey = 20.0
        if self.dose_g == 0:
            return 0
        return (ey / 100 * self.dose_g / self.yield_g) * 100

    def stats(self) -> Dict:
        return {
            "dose_g": self.dose_g,
            "yield_g": self.yield_g,
            "shot_time_s": self.shot_time_s,
            "ratio": round(self.ratio(), 1),
            "flow_rate_g_s": round(self.flow_rate_g_per_s(), 2),
            "time_deviation_pct": round(self.time_deviation_pct(), 1),
            "grind_recommendation": self.grind_recommendation(),
            "dose_recommendation": self.dose_recommendation(),
            "estimated_tds_pct": round(self.estimated_tds_pct(), 2),
        }

def run():
    edc = EspressoDialingCalculator(dose_g=18, yield_g=36, shot_time_s=28, target_time_s=30)
    print(edc.stats())

if __name__ == "__main__":
    run()
