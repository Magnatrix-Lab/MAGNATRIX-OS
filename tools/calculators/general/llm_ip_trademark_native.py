"""Native stdlib module: IP Trademark Checker
Checks trademark conflicts by similarity scoring across classes and descriptions.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set
from enum import Enum

class ConflictLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3

@dataclass
class Trademark:
    name: str
    classes: List[int] = field(default_factory=list)
    description: str = ""

@dataclass
class IPTrademarkChecker:
    proposed: Trademark
    existing: List[Trademark] = field(default_factory=list)

    def class_overlap(self, other: Trademark) -> Set[int]:
        return set(self.proposed.classes) & set(other.classes)

    def word_similarity(self, other: Trademark) -> float:
        words_a = set(self.proposed.name.lower().split())
        words_b = set(other.name.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def conflict_score(self, other: Trademark) -> float:
        class_score = len(self.class_overlap(other)) * 0.3
        sim_score = self.word_similarity(other) * 0.7
        return class_score + sim_score

    def highest_conflict(self) -> Dict:
        if not self.existing:
            return {"level": ConflictLevel.NONE, "trademark": None, "score": 0.0}
        best = max(self.existing, key=lambda t: self.conflict_score(t))
        score = self.conflict_score(best)
        if score >= 0.6:
            level = ConflictLevel.HIGH
        elif score >= 0.3:
            level = ConflictLevel.MEDIUM
        elif score > 0:
            level = ConflictLevel.LOW
        else:
            level = ConflictLevel.NONE
        return {"level": level, "trademark": best.name, "score": round(score, 3)}

    def stats(self) -> Dict:
        return {
            "proposed": self.proposed.name,
            "classes": self.proposed.classes,
            "highest_conflict": self.highest_conflict(),
            "existing_count": len(self.existing),
        }

def run():
    checker = IPTrademarkChecker(
        proposed=Trademark("StarBrew Coffee", [30, 43], "coffee shop and roasted beans"),
        existing=[
            Trademark("StarBrew", [30, 32], "beverages"),
            Trademark("Coffee Star", [30], "ground coffee"),
            Trademark("BrewMaster", [43], "pub services"),
        ]
    )
    print(checker.stats())

if __name__ == "__main__":
    run()
