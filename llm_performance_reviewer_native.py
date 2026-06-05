"""Native stdlib module: Performance Reviewer
Aggregates performance metrics into ratings, goals, and improvement areas.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class Rating(Enum):
    EXCEEDS = 5
    MEETS_PLUS = 4
    MEETS = 3
    NEEDS_IMPROVEMENT = 2
    UNSATISFACTORY = 1

@dataclass
class PerformanceMetric:
    dimension: str
    score: float
    weight: float = 1.0

@dataclass
class PerformanceReviewer:
    employee_name: str
    review_period: str
    metrics: List[PerformanceMetric] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)

    def weighted_score(self) -> float:
        total_weight = sum(m.weight for m in self.metrics)
        if total_weight == 0:
            return 0.0
        return sum(m.score * m.weight for m in self.metrics) / total_weight

    def overall_rating(self) -> Rating:
        ws = self.weighted_score()
        if ws >= 4.5:
            return Rating.EXCEEDS
        elif ws >= 3.5:
            return Rating.MEETS_PLUS
        elif ws >= 2.5:
            return Rating.MEETS
        elif ws >= 1.5:
            return Rating.NEEDS_IMPROVEMENT
        return Rating.UNSATISFACTORY

    def stats(self) -> Dict:
        return {
            "employee": self.employee_name,
            "period": self.review_period,
            "weighted_score": round(self.weighted_score(), 2),
            "overall_rating": self.overall_rating().name,
            "goals_count": len(self.goals),
        }

def run():
    pr = PerformanceReviewer(
        employee_name="Alice Wang",
        review_period="Q2 2024",
        metrics=[
            PerformanceMetric("delivery", 4.5, 2.0),
            PerformanceMetric("quality", 4.0, 2.0),
            PerformanceMetric("collaboration", 3.5, 1.0),
            PerformanceMetric("initiative", 4.0, 1.0),
        ],
        goals=["Improve documentation", "Mentor junior dev"]
    )
    print(pr.stats())

if __name__ == "__main__":
    run()
