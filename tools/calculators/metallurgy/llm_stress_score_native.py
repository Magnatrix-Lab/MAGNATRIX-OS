"""Native stdlib module: Stress Score Calculator
Calculates stress scores from life events and daily hassles.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class LifeEvent:
    event: str
    impact_score: float
    occurred: bool = True
    recent: bool = True

@dataclass
class StressScoreCalculator:
    person_name: str
    events: List[LifeEvent] = field(default_factory=list)

    def total_stress_score(self) -> float:
        return sum(e.impact_score for e in self.events if e.occurred)

    def recent_stress_score(self) -> float:
        return sum(e.impact_score for e in self.events if e.occurred and e.recent)

    def stress_category(self) -> str:
        score = self.total_stress_score()
        if score < 150:
            return "low"
        elif score < 300:
            return "moderate"
        return "high"

    def illness_risk_pct(self) -> float:
        score = self.total_stress_score()
        if score < 150:
            return 30
        elif score < 300:
            return 50
        return 80

    def top_events(self, n: int = 3) -> List[str]:
        sorted_events = sorted([e for e in self.events if e.occurred], key=lambda e: e.impact_score, reverse=True)
        return [e.event for e in sorted_events[:n]]

    def stats(self) -> Dict:
        return {
            "person": self.person_name,
            "total_stress_score": round(self.total_stress_score(), 1),
            "recent_stress_score": round(self.recent_stress_score(), 1),
            "category": self.stress_category(),
            "illness_risk_pct": self.illness_risk_pct(),
            "top_events": self.top_events(),
        }

def run():
    ss = StressScoreCalculator(
        person_name="Taylor",
        events=[
            LifeEvent("death_of_spouse", 100, False),
            LifeEvent("divorce", 73, False),
            LifeEvent("job_loss", 47, True, True),
            LifeEvent("marriage", 50, True, True),
            LifeEvent("retirement", 45, False),
            LifeEvent("pregnancy", 40, False),
            LifeEvent("promotion", 39, True, True),
            LifeEvent("financial_trouble", 38, True, True),
        ]
    )
    print(ss.stats())

if __name__ == "__main__":
    run()
