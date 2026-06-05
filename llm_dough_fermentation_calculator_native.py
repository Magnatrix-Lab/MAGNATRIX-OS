"""Native stdlib module: Dough Fermentation Calculator
Calculates proofing time, temperature effects, and yeast activity.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class DoughFermentationCalculator:
    dough_weight_g: float
    yeast_pct: float
    base_temp_c: float = 25.0
    target_temp_c: float = 25.0
    base_time_hours: float = 2.0

    def temp_factor(self) -> float:
        return 2 ** ((self.target_temp_c - self.base_temp_c) / 10)

    def adjusted_time_hours(self) -> float:
        return self.base_time_hours / self.temp_factor()

    def yeast_activity_factor(self) -> float:
        if self.yeast_pct < 0.5:
            return 0.7
        elif self.yeast_pct < 2:
            return 1.0
        elif self.yeast_pct < 5:
            return 1.3
        return 1.8

    def final_time_hours(self) -> float:
        return self.adjusted_time_hours() / self.yeast_activity_factor()

    def doubling_time_hours(self) -> float:
        return self.final_time_hours() * 0.6

    def overproof_risk_hours(self) -> float:
        return self.final_time_hours() * 1.5

    def cold_retard_time_hours(self) -> float:
        if self.target_temp_c <= 4:
            return self.base_time_hours * 8
        return 0

    def bulk_fermentation_hours(self) -> float:
        return self.final_time_hours()

    def final_proof_hours(self) -> float:
        return self.final_time_hours() * 0.5

    def stats(self) -> Dict:
        return {
            "dough_weight_g": self.dough_weight_g,
            "yeast_pct": self.yeast_pct,
            "target_temp_c": self.target_temp_c,
            "temp_factor": round(self.temp_factor(), 2),
            "adjusted_time_hours": round(self.adjusted_time_hours(), 2),
            "yeast_activity_factor": round(self.yeast_activity_factor(), 2),
            "final_time_hours": round(self.final_time_hours(), 2),
            "doubling_time_hours": round(self.doubling_time_hours(), 2),
            "overproof_risk_hours": round(self.overproof_risk_hours(), 2),
            "bulk_fermentation_hours": round(self.bulk_fermentation_hours(), 2),
            "final_proof_hours": round(self.final_proof_hours(), 2),
        }

def run():
    dfc = DoughFermentationCalculator(dough_weight_g=1000, yeast_pct=1.5, base_temp_c=25, target_temp_c=20, base_time_hours=2)
    print(dfc.stats())

if __name__ == "__main__":
    run()
