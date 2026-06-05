"""Native stdlib module: Vendor Rater
Rates vendors across multiple criteria and computes a composite score.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class RatingScale(Enum):
    EXCELLENT = 5
    GOOD = 4
    AVERAGE = 3
    BELOW_AVERAGE = 2
    POOR = 1

@dataclass
class CriterionScore:
    criterion: str
    score: float
    weight: float = 1.0

@dataclass
class VendorRater:
    vendor_name: str
    category: str
    scores: List[CriterionScore] = field(default_factory=list)
    past_events: int = 0

    def weighted_score(self) -> float:
        total_weight = sum(s.weight for s in self.scores)
        if total_weight == 0:
            return 0.0
        return sum(s.score * s.weight for s in self.scores) / total_weight

    def rating(self) -> RatingScale:
        ws = self.weighted_score()
        if ws >= 4.5:
            return RatingScale.EXCELLENT
        elif ws >= 3.5:
            return RatingScale.GOOD
        elif ws >= 2.5:
            return RatingScale.AVERAGE
        elif ws >= 1.5:
            return RatingScale.BELOW_AVERAGE
        return RatingScale.POOR

    def recommend(self) -> bool:
        return self.weighted_score() >= 3.5 and self.past_events >= 2

    def stats(self) -> Dict:
        return {
            "vendor": self.vendor_name,
            "category": self.category,
            "weighted_score": round(self.weighted_score(), 2),
            "rating": self.rating().name,
            "recommended": self.recommend(),
            "past_events": self.past_events,
        }

def run():
    vr = VendorRater(
        vendor_name="Elite Catering",
        category="catering",
        past_events=5,
        scores=[
            CriterionScore("food_quality", 4.8, 3.0),
            CriterionScore("service", 4.2, 2.0),
            CriterionScore("timeliness", 3.8, 2.0),
            CriterionScore("price", 3.5, 1.0),
            CriterionScore("flexibility", 4.5, 1.0),
        ]
    )
    print(vr.stats())

if __name__ == "__main__":
    run()
