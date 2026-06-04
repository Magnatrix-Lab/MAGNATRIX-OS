"""Drug Interaction Checker — severity, mechanism, contraindications, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class DrugInteraction:
    drug_a: str
    drug_b: str
    severity: str
    mechanism: str

class DrugInteractionChecker:
    def __init__(self):
        self.interactions: Dict[Tuple[str, str], DrugInteraction] = {}

    def add_interaction(self, di: DrugInteraction):
        key = tuple(sorted([di.drug_a, di.drug_b]))
        self.interactions[key] = di

    def check(self, drugs: List[str]) -> List[DrugInteraction]:
        found = []
        for i in range(len(drugs)):
            for j in range(i+1, len(drugs)):
                key = tuple(sorted([drugs[i], drugs[j]]))
                if key in self.interactions:
                    found.append(self.interactions[key])
        return found

    def severity_score(self, interaction: DrugInteraction) -> int:
        scores = {"minor": 1, "moderate": 2, "major": 3, "contraindicated": 4}
        return scores.get(interaction.severity, 0)

    def safe_to_combine(self, drugs: List[str]) -> bool:
        return all(self.severity_score(i) < 3 for i in self.check(drugs))

    def stats(self) -> Dict:
        return {"interactions": len(self.interactions)}

def run():
    dic = DrugInteractionChecker()
    dic.add_interaction(DrugInteraction("Warfarin", "Aspirin", "major", "increased bleeding risk"))
    dic.add_interaction(DrugInteraction("Amlodipine", "Simvastatin", "moderate", "increased statin levels"))
    print("Check:", [(i.drug_a, i.drug_b, i.severity) for i in dic.check(["Warfarin", "Aspirin"])])
    print(dic.stats())

if __name__ == "__main__":
    run()
