"""Learning Analytics — engagement, completion, at-risk, cohort, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Student:
    id: str
    scores: List[float] = field(default_factory=list)
    time_spent: float = 0.0
    logins: int = 0

class LearningAnalytics:
    def __init__(self):
        self.students: Dict[str, Student] = {}

    def add_student(self, s: Student):
        self.students[s.id] = s

    def completion_rate(self) -> float:
        if not self.students:
            return 0.0
        total = sum(len(s.scores) for s in self.students.values())
        return total / (len(self.students) * 10)

    def at_risk(self, threshold: float = 0.5) -> List[str]:
        return [s.id for s in self.students.values() if s.scores and sum(s.scores) / len(s.scores) < threshold * 100]

    def engagement_score(self, student_id: str) -> float:
        s = self.students.get(student_id)
        if not s:
            return 0.0
        return min(1.0, (s.time_spent / 100) * 0.5 + (s.logins / 20) * 0.5)

    def cohort_average(self) -> float:
        if not self.students:
            return 0.0
        all_scores = [sum(s.scores) / len(s.scores) for s in self.students.values() if s.scores]
        return sum(all_scores) / len(all_scores) if all_scores else 0

    def stats(self) -> Dict:
        return {"students": len(self.students), "at_risk": len(self.at_risk()), "cohort_avg": round(self.cohort_average(), 2)}

def run():
    la = LearningAnalytics()
    la.add_student(Student("S1", [80,85,90], 120, 15))
    la.add_student(Student("S2", [40,45,50], 30, 5))
    print(la.stats())
    print("At risk:", la.at_risk())
    print("Engagement S1:", la.engagement_score("S1"))

if __name__ == "__main__":
    run()
