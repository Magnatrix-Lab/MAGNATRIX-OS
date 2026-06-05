"""Veterinary Diagnoser — symptoms, species, weight-based dosing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class VeterinaryDiagnoser:
    species: str = "dog"
    weight_kg: float = 20.0
    age_years: float = 5.0
    symptoms: List[str] = field(default_factory=list)

    def bcs(self, ribs_visible: bool, waist_tuck: bool) -> int:
        if ribs_visible and waist_tuck:
            return 3
        elif not ribs_visible and waist_tuck:
            return 5
        elif not ribs_visible and not waist_tuck:
            return 7
        return 5

    def drug_dose(self, drug: str, mg_per_kg: float) -> float:
        return mg_per_kg * self.weight_kg

    def fluid_rate(self, dehydration_pct: float) -> float:
        maintenance = self.weight_kg * 50
        deficit = self.weight_kg * dehydration_pct * 10
        return maintenance + deficit

    def vaccine_schedule(self) -> List[str]:
        if self.species == "dog":
            return ["DHPP", "Rabies", "Bordetella"]
        elif self.species == "cat":
            return ["FVRCP", "Rabies", "FeLV"]
        return []

    def stats(self) -> Dict:
        return {"species": self.species, "weight": self.weight_kg, "symptoms": len(self.symptoms)}

def run():
    vd = VeterinaryDiagnoser("dog", 25, 3, ["cough", "lethargy"])
    print(vd.stats())
    print("Dose amoxicillin:", vd.drug_dose("amoxicillin", 10))
    print("Vaccines:", vd.vaccine_schedule())

if __name__ == "__main__":
    run()
