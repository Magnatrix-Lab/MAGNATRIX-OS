"""Therapy Planner -- goals, sessions, interventions, outcomes, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class TherapyGoal:
    id: str
    description: str
    target_value: float
    current_value: float
    deadline_weeks: int

class TherapyPlanner:
    def __init__(self):
        self.goals: List[TherapyGoal] = []
        self.sessions: List[Dict] = []

    def add_goal(self, g: TherapyGoal):
        self.goals.append(g)

    def add_session(self, date: str, interventions: List[str], notes: str):
        self.sessions.append({"date": date, "interventions": interventions, "notes": notes})

    def progress_pct(self, goal_id: str) -> float:
        g = next((x for x in self.goals if x.id == goal_id), None)
        if not g or g.target_value == g.current_value:
            return 0.0
        return (g.current_value - 0) / (g.target_value - 0) * 100

    def on_track(self, goal_id: str) -> bool:
        g = next((x for x in self.goals if x.id == goal_id), None)
        if not g:
            return False
        return g.current_value >= g.target_value * 0.5

    def remaining_sessions(self, goal_id: str, sessions_per_week: int = 2) -> int:
        g = next((x for x in self.goals if x.id == goal_id), None)
        if not g:
            return 0
        return g.deadline_weeks * sessions_per_week - len(self.sessions)

    def all_goals_status(self) -> Dict[str, str]:
        return {g.id: "achieved" if g.current_value >= g.target_value else "in_progress" for g in self.goals}

    def stats(self) -> Dict:
        return {"goals": len(self.goals), "sessions": len(self.sessions), "achieved": sum(1 for g in self.goals if g.current_value >= g.target_value)}

def run():
    tp = TherapyPlanner()
    tp.add_goal(TherapyGoal("G1", "Walk 100m", 100, 60, 4))
    tp.add_goal(TherapyGoal("G2", "Lift 5kg", 5, 3, 6))
    tp.add_session("2024-01-15", ["gait training", "strength"], "Good progress")
    print(tp.stats())
    print("Progress G1:", tp.progress_pct("G1"))
    print("Status:", tp.all_goals_status())

if __name__ == "__main__":
    run()
