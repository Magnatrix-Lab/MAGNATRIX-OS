"""Native stdlib module: Body Condition Scorer
Scores animal body condition and calculates nutritional adjustments.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class Species(Enum):
    DOG = "dog"
    CAT = "cat"
    HORSE = "horse"
    CATTLE = "cattle"
    SHEEP = "sheep"

@dataclass
class BodyConditionScorer:
    species: Species
    current_score: float
    ideal_score: float
    body_weight_kg: float

    def score_deviation(self) -> float:
        return self.current_score - self.ideal_score

    def condition(self) -> str:
        dev = self.score_deviation()
        if dev < -1.5:
            return "emaciated"
        elif dev < -0.5:
            return "underweight"
        elif dev < 0.5:
            return "ideal"
        elif dev < 1.5:
            return "overweight"
        return "obese"

    def estimated_weight_adjustment_pct(self) -> float:
        dev = self.score_deviation()
        if self.species in [Species.DOG, Species.CAT]:
            return dev * 5
        elif self.species in [Species.HORSE, Species.CATTLE]:
            return dev * 3
        return dev * 4

    def target_weight_kg(self) -> float:
        adj = self.estimated_weight_adjustment_pct()
        return self.body_weight_kg * (1 - adj / 100)

    def calorie_adjustment_pct(self) -> float:
        dev = self.score_deviation()
        if dev > 0:
            return -dev * 10
        elif dev < 0:
            return -dev * 15
        return 0

    def stats(self) -> Dict:
        return {
            "species": self.species.value,
            "current_score": self.current_score,
            "ideal_score": self.ideal_score,
            "condition": self.condition(),
            "body_weight_kg": self.body_weight_kg,
            "target_weight_kg": round(self.target_weight_kg(), 1),
            "calorie_adjustment_pct": round(self.calorie_adjustment_pct(), 1),
        }

def run():
    bcs = BodyConditionScorer(species=Species.DOG, current_score=7, ideal_score=5, body_weight_kg=30)
    print(bcs.stats())

if __name__ == "__main__":
    run()
