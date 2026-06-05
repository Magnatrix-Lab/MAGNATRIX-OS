"""Native stdlib module: Drug Interaction Calculator
Assesses drug interaction severity and mechanism types.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class InteractionType(Enum):
    SYNERGY = "synergy"
    ANTAGONISM = "antagonism"
    ADDITIVE = "additive"
    POTENTIATION = "potentiation"
    INHIBITION = "inhibition"

class SeverityLevel(Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CONTRAINDICATED = "contraindicated"

@dataclass
class DrugInteractionPair:
    drug_a: str
    drug_b: str
    interaction_type: InteractionType
    severity: SeverityLevel
    effect_description: str

@dataclass
class DrugInteractionCalculator:
    patient_id: str
    interactions: List[DrugInteractionPair] = field(default_factory=list)

    def severe_interactions(self) -> List[DrugInteractionPair]:
        return [i for i in self.interactions if i.severity in [SeverityLevel.MAJOR, SeverityLevel.CONTRAINDICATED]]

    def by_severity(self) -> Dict[str, int]:
        counts = {}
        for i in self.interactions:
            counts[i.severity.value] = counts.get(i.severity.value, 0) + 1
        return counts

    def by_type(self) -> Dict[str, int]:
        counts = {}
        for i in self.interactions:
            counts[i.interaction_type.value] = counts.get(i.interaction_type.value, 0) + 1
        return counts

    def has_contraindicated(self) -> bool:
        return any(i.severity == SeverityLevel.CONTRAINDICATED for i in self.interactions)

    def stats(self) -> Dict:
        return {
            "patient": self.patient_id,
            "total_interactions": len(self.interactions),
            "severe_count": len(self.severe_interactions()),
            "contraindicated": self.has_contraindicated(),
            "by_severity": self.by_severity(),
            "by_type": self.by_type(),
        }

def run():
    dic = DrugInteractionCalculator(
        patient_id="P-001",
        interactions=[
            DrugInteractionPair("Warfarin", "Aspirin", InteractionType.POTENTIATION, SeverityLevel.MAJOR, "Increased bleeding risk"),
            DrugInteractionPair("Metformin", "Contrast dye", InteractionType.INHIBITION, SeverityLevel.MODERATE, "Lactic acidosis risk"),
            DrugInteractionPair("Simvastatin", "Grapefruit", InteractionType.INHIBITION, SeverityLevel.MINOR, "Increased statin levels"),
        ]
    )
    print(dic.stats())

if __name__ == "__main__":
    run()
