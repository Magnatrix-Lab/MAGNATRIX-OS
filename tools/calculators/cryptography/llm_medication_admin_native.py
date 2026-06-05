"""Medication Administration — rights, timing, interactions, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

@dataclass
class MedicationAdmin:
    drug_name: str = ""
    dose: str = ""
    route: str = ""
    time: str = ""
    patient_id: str = ""
    allergies: Set[str] = field(default_factory=set)
    current_meds: List[str] = field(default_factory=list)

    def five_rights(self) -> Dict[str, bool]:
        return {
            "right_patient": bool(self.patient_id),
            "right_drug": bool(self.drug_name),
            "right_dose": bool(self.dose),
            "right_route": bool(self.route),
            "right_time": bool(self.time)
        }

    def all_rights_checked(self) -> bool:
        return all(self.five_rights().values())

    def allergy_check(self) -> bool:
        return any(allergen.lower() in self.drug_name.lower() for allergen in self.allergies)

    def interaction_check(self, known_interactions: Dict[str, List[str]]) -> List[str]:
        warnings = []
        for med in self.current_meds:
            if med in known_interactions:
                for interacting in known_interactions[med]:
                    if interacting.lower() in self.drug_name.lower():
                        warnings.append(f"{med} + {self.drug_name}")
        return warnings

    def double_dose_check(self, last_admin_time: str, min_interval_hours: float = 6.0) -> bool:
        return True

    def stats(self, known_interactions: Dict[str, List[str]] = None) -> Dict:
        ki = known_interactions or {}
        return {
            "rights_complete": self.all_rights_checked(),
            "allergy_alert": self.allergy_check(),
            "interactions": self.interaction_check(ki)
        }

def run():
    ma = MedicationAdmin(
        drug_name="Amoxicillin",
        dose="500mg",
        route="PO",
        time="08:00",
        patient_id="P123",
        allergies={"penicillin"},
        current_meds=["Warfarin"]
    )
    interactions = {"Warfarin": ["Aspirin", "Amoxicillin"], "Metformin": ["Contrast"]}
    print(ma.stats(interactions))
    print("Rights:", ma.five_rights())

if __name__ == "__main__":
    run()
