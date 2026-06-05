"""Native stdlib module: Perfume Alcohol Calculator
Calculates alcohol percentage, maceration, and dilution needs.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PerfumeAlcoholCalculator:
    batch_volume_ml: float
    desired_alcohol_pct: float = 80.0
    concentrate_pct: float = 15.0

    def alcohol_volume_ml(self) -> float:
        return self.batch_volume_ml * (self.desired_alcohol_pct / 100)

    def concentrate_volume_ml(self) -> float:
        return self.batch_volume_ml * (self.concentrate_pct / 100)

    def water_volume_ml(self) -> float:
        return self.batch_volume_ml - self.alcohol_volume_ml() - self.concentrate_volume_ml()

    def alcohol_strength_needed(self) -> float:
        if self.batch_volume_ml == 0:
            return 0
        return (self.desired_alcohol_pct / (self.desired_alcohol_pct / 100 + self.water_volume_ml() / self.batch_volume_ml)) * 100

    def maceration_time_days(self) -> int:
        if self.concentrate_pct >= 20:
            return 45
        elif self.concentrate_pct >= 10:
            return 30
        return 21

    def aging_time_weeks(self) -> int:
        if self.concentrate_pct >= 20:
            return 8
        elif self.concentrate_pct >= 10:
            return 6
        return 4

    def recommended_alcohol_type(self) -> str:
        if self.desired_alcohol_pct >= 90:
            return "perfumers_alcohol_190_proof"
        elif self.desired_alcohol_pct >= 80:
            return "perfumers_alcohol_160_proof"
        return "vodka_80_proof_not_recommended"

    def stats(self) -> Dict:
        return {
            "batch_volume_ml": self.batch_volume_ml,
            "desired_alcohol_pct": self.desired_alcohol_pct,
            "concentrate_pct": self.concentrate_pct,
            "alcohol_volume_ml": round(self.alcohol_volume_ml(), 1),
            "concentrate_volume_ml": round(self.concentrate_volume_ml(), 1),
            "water_volume_ml": round(self.water_volume_ml(), 1),
            "maceration_days": self.maceration_time_days(),
            "aging_weeks": self.aging_time_weeks(),
            "recommended_alcohol": self.recommended_alcohol_type(),
        }

def run():
    pac = PerfumeAlcoholCalculator(batch_volume_ml=100, desired_alcohol_pct=80, concentrate_pct=15)
    print(pac.stats())

if __name__ == "__main__":
    run()
