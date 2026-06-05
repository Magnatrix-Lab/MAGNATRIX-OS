"""Drug Interaction Checker (Pharmacy) — CYP, mechanism, severity, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class DrugInteractionPharm:
    drug_a: str = ""
    drug_b: str = ""
    mechanism: str = ""
    severity: str = ""
    clinical_effect: str = ""

class DrugInteractionCheckerPharm:
    def __init__(self):
        self.interactions: List[DrugInteractionPharm] = []

    def add_interaction(self, di: DrugInteractionPharm):
        self.interactions.append(di)

    def check(self, drug_list: List[str]) -> List[DrugInteractionPharm]:
        found = []
        for i in range(len(drug_list)):
            for j in range(i+1, len(drug_list)):
                for di in self.interactions:
                    if (di.drug_a.lower() in drug_list[i].lower() and di.drug_b.lower() in drug_list[j].lower()) or                        (di.drug_a.lower() in drug_list[j].lower() and di.drug_b.lower() in drug_list[i].lower()):
                        found.append(di)
        return found

    def severity_rank(self, severity: str) -> int:
        ranks = {"contraindicated": 4, "major": 3, "moderate": 2, "minor": 1, "unknown": 0}
        return ranks.get(severity.lower(), 0)

    def by_mechanism(self, mechanism: str) -> List[DrugInteractionPharm]:
        return [di for di in self.interactions if mechanism.lower() in di.mechanism.lower()]

    def cyp_interactions(self) -> List[DrugInteractionPharm]:
        return [di for di in self.interactions if "CYP" in di.mechanism.upper()]

    def stats(self, drug_list: List[str]) -> Dict:
        found = self.check(drug_list)
        return {"interactions": len(found), "major": sum(1 for f in found if f.severity.lower() == "major")}

def run():
    dic = DrugInteractionCheckerPharm()
    dic.add_interaction(DrugInteractionPharm("Warfarin", "Fluconazole", "CYP2C9 inhibition", "Major", "increased bleeding risk"))
    dic.add_interaction(DrugInteractionPharm("Simvastatin", "Clarithromycin", "CYP3A4 inhibition", "Major", "increased myopathy risk"))
    print(dic.stats(["Warfarin", "Fluconazole", "Aspirin"]))
    print("CYP interactions:", len(dic.cyp_interactions()))

if __name__ == "__main__":
    run()
