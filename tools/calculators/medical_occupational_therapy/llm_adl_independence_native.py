"""Native stdlib module: ADL Independence Calculator
Scores activities of daily living independence and assistance needs.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class IndependenceLevel(Enum):
    INDEPENDENT = 7
    MODIFIED_INDEPENDENT = 6
    SUPERVISION = 5
    MINIMAL_ASSIST = 4
    MODERATE_ASSIST = 3
    MAXIMAL_ASSIST = 2
    TOTAL_ASSIST = 1

@dataclass
class ADLItem:
    activity: str
    score: IndependenceLevel

@dataclass
class ADLIndependenceCalculator:
    patient_name: str
    adl_items: List[ADLItem] = field(default_factory=list)

    def total_score(self) -> int:
        return sum(s.score.value for s in self.adl_items)

    def max_possible_score(self) -> int:
        return len(self.adl_items) * 7

    def independence_pct(self) -> float:
        if self.max_possible_score() == 0:
            return 0.0
        return (self.total_score() / self.max_possible_score()) * 100

    def assistance_needed_count(self) -> int:
        return sum(1 for s in self.adl_items if s.score.value < 5)

    def fully_independent_count(self) -> int:
        return sum(1 for s in self.adl_items if s.score == IndependenceLevel.INDEPENDENT)

    def by_score(self) -> Dict[str, int]:
        counts = {}
        for s in self.adl_items:
            counts[s.score.name] = counts.get(s.score.name, 0) + 1
        return counts

    def fim_equivalent(self) -> int:
        return self.total_score()

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "activities": len(self.adl_items),
            "total_score": self.total_score(),
            "max_score": self.max_possible_score(),
            "independence_pct": round(self.independence_pct(), 1),
            "assistance_needed": self.assistance_needed_count(),
            "fully_independent": self.fully_independent_count(),
            "fim_equivalent": self.fim_equivalent(),
        }

def run():
    adl = ADLIndependenceCalculator(
        patient_name="Patient-X",
        adl_items=[
            ADLItem("eating", IndependenceLevel.INDEPENDENT),
            ADLItem("grooming", IndependenceLevel.MODIFIED_INDEPENDENT),
            ADLItem("bathing", IndependenceLevel.MINIMAL_ASSIST),
            ADLItem("dressing_upper", IndependenceLevel.INDEPENDENT),
            ADLItem("dressing_lower", IndependenceLevel.MODERATE_ASSIST),
            ADLItem("toileting", IndependenceLevel.MINIMAL_ASSIST),
            ADLItem("transfers", IndependenceLevel.MODERATE_ASSIST),
            ADLItem("mobility", IndependenceLevel.MODIFIED_INDEPENDENT),
        ]
    )
    print(adl.stats())

if __name__ == "__main__":
    run()
