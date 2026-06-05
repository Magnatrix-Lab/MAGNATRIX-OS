"""Native stdlib module: Ethical Dilemma Calculator
Evaluates ethical dilemmas by utilitarian and deontological frameworks.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class EthicalFramework(Enum):
    UTILITARIAN = "utilitarian"
    DEONTOLOGICAL = "deontological"
    VIRTUE_ETHICS = "virtue_ethics"
    CARE_ETHICS = "care_ethics"

@dataclass
class Consequence:
    stakeholder: str
    utility_change: float
    rights_affected: int
    autonomy_impact: float

@dataclass
class EthicalDilemmaCalculator:
    dilemma_name: str
    action_a: str
    action_b: str
    consequences_a: List[Consequence] = field(default_factory=list)
    consequences_b: List[Consequence] = field(default_factory=list)

    def total_utility(self, consequences: List[Consequence]) -> float:
        return sum(c.utility_change for c in consequences)

    def total_rights_affected(self, consequences: List[Consequence]) -> int:
        return sum(c.rights_affected for c in consequences)

    def total_autonomy_impact(self, consequences: List[Consequence]) -> float:
        return sum(c.autonomy_impact for c in consequences)

    def utilitarian_recommendation(self) -> str:
        util_a = self.total_utility(self.consequences_a)
        util_b = self.total_utility(self.consequences_b)
        if util_a > util_b:
            return self.action_a
        elif util_b > util_a:
            return self.action_b
        return "tie"

    def deontological_recommendation(self) -> str:
        rights_a = self.total_rights_affected(self.consequences_a)
        rights_b = self.total_rights_affected(self.consequences_b)
        if rights_a < rights_b:
            return self.action_a
        elif rights_b < rights_a:
            return self.action_b
        return "tie"

    def stats(self) -> Dict:
        return {
            "dilemma": self.dilemma_name,
            "utilitarian_choice": self.utilitarian_recommendation(),
            "deontological_choice": self.deontological_recommendation(),
            "utility_a": round(self.total_utility(self.consequences_a), 2),
            "utility_b": round(self.total_utility(self.consequences_b), 2),
            "rights_a": self.total_rights_affected(self.consequences_a),
            "rights_b": self.total_rights_affected(self.consequences_b),
        }

def run():
    edc = EthicalDilemmaCalculator(
        dilemma_name="Trolley Problem",
        action_a="pull_lever",
        action_b="do_nothing",
        consequences_a=[
            Consequence("worker1", -1, 1, -1),
            Consequence("worker2", -1, 1, -1),
            Consequence("worker3", -1, 1, -1),
            Consequence("worker4", -1, 1, -1),
            Consequence("worker5", -1, 1, -1),
        ],
        consequences_b=[
            Consequence("worker1", 0, 0, 0),
            Consequence("worker2", 0, 0, 0),
            Consequence("worker3", 0, 0, 0),
            Consequence("worker4", 0, 0, 0),
            Consequence("worker5", -1, 1, -1),
        ]
    )
    print(edc.stats())

if __name__ == "__main__":
    run()
