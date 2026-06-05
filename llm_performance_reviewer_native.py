"""Performance Reviewer — goals, competencies, ratings, calibration, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class PerformanceReviewer:
    goals: Dict[str, float] = field(default_factory=dict)
    """goal -> achievement_pct"""
    competencies: Dict[str, float] = field(default_factory=dict)
    """competency -> score 1-5"""
    weights: Dict[str, float] = field(default_factory=dict)

    def goal_achievement(self) -> float:
        if not self.goals:
            return 0.0
        return sum(self.goals.values()) / len(self.goals)

    def competency_score(self) -> float:
        if not self.competencies:
            return 0.0
        return sum(self.competencies.values()) / len(self.competencies)

    def overall_rating(self, goal_weight: float = 0.6) -> float:
        return self.goal_achievement() * goal_weight + (self.competency_score() / 5) * (1 - goal_weight) * 100

    def rating_category(self) -> str:
        o = self.overall_rating()
        if o >= 90: return "exceptional"
        elif o >= 75: return "exceeds"
        elif o >= 60: return "meets"
        elif o >= 40: return "partially_meets"
        return "needs_improvement"

    def calibration_delta(self, rater_bias: float = 0.0) -> float:
        return self.overall_rating() - rater_bias

    def stats(self) -> Dict:
        return {
            "goal_achievement": round(self.goal_achievement(), 3),
            "competency": round(self.competency_score(), 2),
            "overall": round(self.overall_rating(), 1),
            "category": self.rating_category()
        }

def run():
    pr = PerformanceReviewer(
        goals={"revenue": 0.95, "projects": 1.0, "training": 0.8},
        competencies={"communication": 4, "technical": 5, "leadership": 3},
    )
    print(pr.stats())

if __name__ == "__main__":
    run()
