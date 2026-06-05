"""Native stdlib module: Muscle Strength Calculator
Scores MMT grades and calculates muscle strength ratios.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class MMTGrade(Enum):
    ZERO = 0
    TRACE = 1
    POOR = 2
    FAIR = 3
    GOOD = 4
    NORMAL = 5

@dataclass
class MuscleTest:
    muscle_name: str
    grade: MMTGrade
    side: str = "right"

@dataclass
class MuscleStrengthCalculator:
    patient_name: str
    tests: List[MuscleTest] = field(default_factory=list)

    def total_score(self) -> int:
        return sum(t.grade.value for t in self.tests)

    def max_score(self) -> int:
        return len(self.tests) * 5

    def strength_pct(self) -> float:
        if self.max_score() == 0:
            return 0.0
        return (self.total_score() / self.max_score()) * 100

    def avg_grade(self) -> float:
        if not self.tests:
            return 0.0
        return self.total_score() / len(self.tests)

    def normal_muscles(self) -> List[str]:
        return [t.muscle_name for t in self.tests if t.grade == MMTGrade.NORMAL]

    def weak_muscles(self) -> List[str]:
        return [t.muscle_name for t in self.tests if t.grade.value < 3]

    def by_grade(self) -> Dict[str, int]:
        counts = {}
        for t in self.tests:
            counts[t.grade.name] = counts.get(t.grade.name, 0) + 1
        return counts

    def side_comparison(self, muscle_name: str) -> Dict:
        right = next((t.grade.value for t in self.tests if t.muscle_name == muscle_name and t.side == "right"), 0)
        left = next((t.grade.value for t in self.tests if t.muscle_name == muscle_name and t.side == "left"), 0)
        if right == 0:
            return {"right": right, "left": left, "diff": 0}
        return {"right": right, "left": left, "diff": left - right}

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "muscles_tested": len(self.tests),
            "total_score": self.total_score(),
            "max_score": self.max_score(),
            "strength_pct": round(self.strength_pct(), 1),
            "avg_grade": round(self.avg_grade(), 1),
            "weak_muscles": self.weak_muscles(),
            "normal_muscles": self.normal_muscles(),
        }

def run():
    msc = MuscleStrengthCalculator(
        patient_name="Patient-C",
        tests=[
            MuscleTest("deltoid", MMTGrade.NORMAL, "right"),
            MuscleTest("deltoid", MMTGrade.GOOD, "left"),
            MuscleTest("biceps", MMTGrade.NORMAL, "right"),
            MuscleTest("biceps", MMTGrade.NORMAL, "left"),
            MuscleTest("triceps", MMTGrade.FAIR, "right"),
            MuscleTest("triceps", MMTGrade.FAIR, "left"),
            MuscleTest("quadriceps", MMTGrade.GOOD, "right"),
            MuscleTest("quadriceps", MMTGrade.NORMAL, "left"),
            MuscleTest("hamstrings", MMTGrade.FAIR, "right"),
            MuscleTest("hamstrings", MMTGrade.POOR, "left"),
        ]
    )
    print(msc.stats())

if __name__ == "__main__":
    run()
