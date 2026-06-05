"""Native stdlib module: Interview Scheduler
Schedules interview panels while checking for conflicts and availability.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set
from datetime import datetime, timedelta

@dataclass
class Interviewer:
    name: str
    available_slots: List[str] = field(default_factory=list)
    role: str = "panel"

@dataclass
class InterviewScheduler:
    candidate_name: str
    interviewers: List[Interviewer] = field(default_factory=list)
    duration_minutes: int = 60

    def common_slots(self) -> List[str]:
        if not self.interviewers:
            return []
        common = set(self.interviewers[0].available_slots)
        for i in self.interviewers[1:]:
            common &= set(i.available_slots)
        return sorted(common)

    def panel_size(self) -> int:
        return len(self.interviewers)

    def schedule(self, slot: str) -> Dict:
        if slot not in self.common_slots():
            return {"error": "Slot not available for all interviewers"}
        return {
            "candidate": self.candidate_name,
            "slot": slot,
            "duration_min": self.duration_minutes,
            "panel": [i.name for i in self.interviewers],
        }

    def stats(self) -> Dict:
        return {
            "panel_size": self.panel_size(),
            "common_slots": self.common_slots(),
            "candidate": self.candidate_name,
        }

def run():
    is_ = InterviewScheduler(
        candidate_name="John Smith",
        interviewers=[
            Interviewer("Alice", ["2024-06-10T09:00", "2024-06-10T10:00", "2024-06-10T14:00"], "lead"),
            Interviewer("Bob", ["2024-06-10T10:00", "2024-06-10T14:00"], "tech"),
            Interviewer("Carol", ["2024-06-10T09:00", "2024-06-10T10:00", "2024-06-10T15:00"], "hr"),
        ]
    )
    print(is_.stats())
    print(is_.schedule("2024-06-10T10:00"))

if __name__ == "__main__":
    run()
