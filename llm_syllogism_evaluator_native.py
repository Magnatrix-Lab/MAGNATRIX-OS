"""Native stdlib module: Syllogism Evaluator
Evaluates categorical syllogisms for validity using mood and figure analysis.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class PropositionType(Enum):
    A = "A"  # All S are P
    E = "E"  # No S are P
    I = "I"  # Some S are P
    O = "O"  # Some S are not P

@dataclass
class SyllogismEvaluator:
    major_premise: PropositionType
    minor_premise: PropositionType
    conclusion: PropositionType
    figure: int  # 1, 2, 3, or 4

    def mood(self) -> str:
        return f"{self.major_premise.value}{self.minor_premise.value}{self.conclusion.value}"

    def valid_forms(self) -> List[str]:
        return [
            "AAA1", "AAI1", "AII1", "EAE1", "EIO1", "AOO1",
            "AEE2", "AEO2", "AOO2", "EAE2", "EIO2", "EIO2",
            "AAI3", "AII3", "EAO3", "EIO3", "IAI3", "OAO3",
            "AAI4", "AEE4", "EAO4", "EIO4", "IAI4",
        ]

    def is_valid(self) -> bool:
        form = f"{self.mood()}{self.figure}"
        return form in self.valid_forms()

    def has_valid_mood(self) -> bool:
        return self.mood() in ["AAA", "AAI", "AEE", "AEO", "AII", "AOO", "EAE", "EAO", "EIO", "IAI", "OAO"]

    def fallacy(self) -> str:
        if self.is_valid():
            return "none"
        if self.conclusion == PropositionType.A and (self.major_premise != PropositionType.A or self.minor_premise != PropositionType.A):
            return "illicit_major/minor"
        if self.conclusion == PropositionType.E and (self.major_premise == PropositionType.I or self.minor_premise == PropositionType.I):
            return "illicit_subalternation"
        return "undetermined"

    def stats(self) -> Dict:
        return {
            "mood": self.mood(),
            "figure": self.figure,
            "valid": self.is_valid(),
            "valid_mood": self.has_valid_mood(),
            "fallacy": self.fallacy(),
        }

def run():
    se = SyllogismEvaluator(major_premise=PropositionType.A, minor_premise=PropositionType.A, conclusion=PropositionType.A, figure=1)
    print(se.stats())

if __name__ == "__main__":
    run()
