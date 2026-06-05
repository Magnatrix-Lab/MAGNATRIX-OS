"""Native stdlib module: Freeness Calculator
Calculates freeness, drainability, and beating degree for pulp processing.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class BeatingDegree(Enum):
    FREE = "free"
    SLIGHTLY_BEATEN = "slightly_beaten"
    MODERATELY_BEATEN = "moderately_beaten"
    WELL_BEATEN = "well_beaten"
    HIGHLY_BEATEN = "highly_beaten"

@dataclass
class FreenessCalculator:
    pulp_type: str
    beating_time_min: float
    beater_type: str
    initial_freeness_ml: float

    def freeness_drop_ml(self) -> float:
        if self.beater_type == "jordan":
            rate = 5
        elif self.beater_type == "pfi":
            rate = 8
        elif self.beater_type == "hollander":
            rate = 3
        else:
            rate = 4
        return self.beating_time_min * rate

    def final_freeness_ml(self) -> float:
        return max(0, self.initial_freeness_ml - self.freeness_drop_ml())

    def beating_degree(self) -> BeatingDegree:
        ff = self.final_freeness_ml()
        if ff > 500:
            return BeatingDegree.FREE
        elif ff > 300:
            return BeatingDegree.SLIGHTLY_BEATEN
        elif ff > 200:
            return BeatingDegree.MODERATELY_BEATEN
        elif ff > 100:
            return BeatingDegree.WELL_BEATEN
        return BeatingDegree.HIGHLY_BEATEN

    def drain_time_s(self) -> float:
        if self.final_freeness_ml() == 0:
            return 999.0
        return 1000 / self.final_freeness_ml()

    def wet_web_strength_estimate(self) -> float:
        if self.final_freeness_ml() > 400:
            return 1.0
        return 1.0 + (400 - self.final_freeness_ml()) / 100

    def stats(self) -> Dict:
        return {
            "pulp_type": self.pulp_type,
            "beating_time_min": self.beating_time_min,
            "freeness_drop_ml": round(self.freeness_drop_ml(), 1),
            "final_freeness_ml": round(self.final_freeness_ml(), 1),
            "beating_degree": self.beating_degree().value,
            "drain_time_s": round(self.drain_time_s(), 2),
        }

def run():
    fc = FreenessCalculator(pulp_type="Kraft Pine", beating_time_min=30, beater_type="jordan", initial_freeness_ml=700)
    print(fc.stats())

if __name__ == "__main__":
    run()
