"""Native stdlib module: Language Milestone Tracker
Tracks language development milestones against age norms.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Milestone:
    skill: str
    expected_age_months: float
    achieved_age_months: float

@dataclass
class LanguageMilestoneTracker:
    child_name: str
    current_age_months: float
    milestones: List[Milestone] = field(default_factory=list)

    def achieved_count(self) -> int:
        return sum(1 for m in self.milestones if m.achieved_age_months <= self.current_age_months)

    def delayed_count(self) -> int:
        return sum(1 for m in self.milestones if m.achieved_age_months > m.expected_age_months + 3)

    def ahead_count(self) -> int:
        return sum(1 for m in self.milestones if m.achieved_age_months < m.expected_age_months - 3)

    def milestone_pct(self) -> float:
        if not self.milestones:
            return 0.0
        return (self.achieved_count() / len(self.milestones)) * 100

    def avg_delay_months(self) -> float:
        delays = [m.achieved_age_months - m.expected_age_months for m in self.milestones if m.achieved_age_months > m.expected_age_months]
        if not delays:
            return 0.0
        return sum(delays) / len(delays)

    def development_status(self) -> str:
        if self.delayed_count() == 0:
            return "on_track"
        elif self.delayed_count() <= 2:
            return "mild_delay"
        elif self.delayed_count() <= 4:
            return "moderate_delay"
        return "significant_delay"

    def stats(self) -> Dict:
        return {
            "child": self.child_name,
            "current_age_months": self.current_age_months,
            "total_milestones": len(self.milestones),
            "achieved": self.achieved_count(),
            "delayed": self.delayed_count(),
            "milestone_pct": round(self.milestone_pct(), 1),
            "avg_delay_months": round(self.avg_delay_months(), 1),
            "status": self.development_status(),
        }

def run():
    lmt = LanguageMilestoneTracker(
        child_name="Emma",
        current_age_months=24,
        milestones=[
            Milestone("first_words", 12, 11),
            Milestone("two_word_phrases", 18, 20),
            Milestone("50_words", 18, 19),
            Milestone("follows_commands", 15, 14),
            Milestone("points_to_objects", 12, 13),
            Milestone("uses_gestures", 9, 8),
            Milestone("responds_to_name", 6, 6),
            Milestone("babbles", 6, 5),
        ]
    )
    print(lmt.stats())

if __name__ == "__main__":
    run()
