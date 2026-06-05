"""Native stdlib module: Burnout Assessment
Assesses burnout risk using workload, exhaustion, and cynicism scores.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class RiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"

@dataclass
class BurnoutDimension:
    name: str
    score: float
    max_score: float = 7.0

@dataclass
class BurnoutAssessment:
    person_name: str
    dimensions: List[BurnoutDimension] = field(default_factory=list)

    def total_score(self) -> float:
        return sum(d.score for d in self.dimensions)

    def avg_score(self) -> float:
        if not self.dimensions:
            return 0.0
        return self.total_score() / len(self.dimensions)

    def risk_level(self) -> RiskLevel:
        avg = self.avg_score()
        if avg < 2.5:
            return RiskLevel.LOW
        elif avg < 4.0:
            return RiskLevel.MODERATE
        elif avg < 5.5:
            return RiskLevel.HIGH
        return RiskLevel.SEVERE

    def highest_dimension(self) -> str:
        if not self.dimensions:
            return ""
        return max(self.dimensions, key=lambda d: d.score).name

    def stats(self) -> Dict:
        return {
            "person": self.person_name,
            "avg_score": round(self.avg_score(), 2),
            "risk_level": self.risk_level().value,
            "highest_dimension": self.highest_dimension(),
            "dimensions": {d.name: round(d.score, 1) for d in self.dimensions},
        }

def run():
    ba = BurnoutAssessment(
        person_name="Morgan",
        dimensions=[
            BurnoutDimension("exhaustion", 5.5, 7),
            BurnoutDimension("cynicism", 4.0, 7),
            BurnoutDimension("professional_efficacy", 2.5, 7),
            BurnoutDimension("workload", 6.0, 7),
            BurnoutDimension("work_life_balance", 5.0, 7),
        ]
    )
    print(ba.stats())

if __name__ == "__main__":
    run()
