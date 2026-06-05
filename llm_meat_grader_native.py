"""Native stdlib module: Meat Grader
Evaluates meat quality grades based on marbling, maturity, and yield.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class Grade(Enum):
    PRIME = "prime"
    CHOICE = "choice"
    SELECT = "select"
    STANDARD = "standard"

@dataclass
class MeatGrader:
    marbling_score: int
    maturity_months: int
    yield_grade: int

    def quality_grade(self) -> Grade:
        if self.marbling_score >= 8 and self.maturity_months <= 24:
            return Grade.PRIME
        elif self.marbling_score >= 5 and self.maturity_months <= 30:
            return Grade.CHOICE
        elif self.marbling_score >= 3:
            return Grade.SELECT
        return Grade.STANDARD

    def is_young(self) -> bool:
        return self.maturity_months <= 30

    def stats(self) -> Dict:
        return {
            "quality_grade": self.quality_grade().value,
            "young": self.is_young(),
            "yield_grade": self.yield_grade,
        }

def run():
    grader = MeatGrader(marbling_score=7, maturity_months=22, yield_grade=2)
    print(grader.stats())

if __name__ == "__main__":
    run()
