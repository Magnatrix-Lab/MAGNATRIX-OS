"""Native stdlib module: Argument Map Builder
Builds argument maps with premises, conclusions, and strength scores.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class PremiseType(Enum):
    FACT = "fact"
    OPINION = "opinion"
    ASSUMPTION = "assumption"
    EVIDENCE = "evidence"

@dataclass
class Premise:
    statement: str
    premise_type: PremiseType
    strength: float  # 0-1
    supports: List[str] = field(default_factory=list)

@dataclass
class ArgumentMapBuilder:
    argument_name: str
    conclusion: str
    premises: List[Premise] = field(default_factory=list)

    def total_strength(self) -> float:
        if not self.premises:
            return 0.0
        return sum(p.strength for p in self.premises) / len(self.premises)

    def supporting_strength(self) -> float:
        supporting = [p for p in self.premises if p.premise_type in [PremiseType.FACT, PremiseType.EVIDENCE]]
        if not supporting:
            return 0.0
        return sum(p.strength for p in supporting) / len(supporting)

    def assumption_count(self) -> int:
        return sum(1 for p in self.premises if p.premise_type == PremiseType.ASSUMPTION)

    def evidence_count(self) -> int:
        return sum(1 for p in self.premises if p.premise_type == PremiseType.EVIDENCE)

    def argument_strength(self) -> str:
        ts = self.total_strength()
        if ts >= 0.8:
            return "strong"
        elif ts >= 0.6:
            return "moderate"
        elif ts >= 0.4:
            return "weak"
        return "very_weak"

    def stats(self) -> Dict:
        return {
            "argument": self.argument_name,
            "conclusion": self.conclusion,
            "premises": len(self.premises),
            "total_strength": round(self.total_strength(), 2),
            "supporting_strength": round(self.supporting_strength(), 2),
            "assumptions": self.assumption_count(),
            "evidence": self.evidence_count(),
            "argument_strength": self.argument_strength(),
        }

def run():
    amb = ArgumentMapBuilder(
        argument_name="Climate Change",
        conclusion="Climate change is primarily caused by human activities",
        premises=[
            Premise("CO2 levels have risen since industrialization", PremiseType.EVIDENCE, 0.95, ["conclusion"]),
            Premise("Temperature correlates with CO2", PremiseType.EVIDENCE, 0.9, ["conclusion"]),
            Premise("Natural cycles alone cannot explain warming", PremiseType.EVIDENCE, 0.85, ["conclusion"]),
            Premise("Human emissions are the main source of CO2 increase", PremiseType.ASSUMPTION, 0.8, ["conclusion"]),
        ]
    )
    print(amb.stats())

if __name__ == "__main__":
    run()
