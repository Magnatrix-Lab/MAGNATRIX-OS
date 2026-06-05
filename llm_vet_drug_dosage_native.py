"""Native stdlib module: Veterinary Drug Dosage Calculator
Calculates animal drug dosages by weight, species, and condition.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class Species(Enum):
    DOG = "dog"
    CAT = "cat"
    HORSE = "horse"
    CATTLE = "cattle"
    RABBIT = "rabbit"
    BIRD = "bird"

@dataclass
class VeterinaryDrugDosage:
    drug_name: str
    species: Species
    body_weight_kg: float
    standard_dose_mg_kg: float
    frequency_per_day: int = 2
    duration_days: int = 7

    def species_factor(self) -> float:
        factors = {Species.DOG: 1.0, Species.CAT: 1.0, Species.HORSE: 0.5, Species.CATTLE: 0.5, Species.RABBIT: 2.0, Species.BIRD: 3.0}
        return factors.get(self.species, 1.0)

    def single_dose_mg(self) -> float:
        return self.body_weight_kg * self.standard_dose_mg_kg * self.species_factor()

    def daily_dose_mg(self) -> float:
        return self.single_dose_mg() * self.frequency_per_day

    def total_dose_mg(self) -> float:
        return self.daily_dose_mg() * self.duration_days

    def volume_ml(self, concentration_mg_ml: float) -> float:
        if concentration_mg_ml == 0:
            return 0.0
        return self.single_dose_mg() / concentration_mg_ml

    def stats(self, concentration_mg_ml: float = 0) -> Dict:
        return {
            "drug": self.drug_name,
            "species": self.species.value,
            "weight_kg": self.body_weight_kg,
            "single_dose_mg": round(self.single_dose_mg(), 2),
            "daily_dose_mg": round(self.daily_dose_mg(), 2),
            "total_dose_mg": round(self.total_dose_mg(), 2),
            "volume_ml": round(self.volume_ml(concentration_mg_ml), 2) if concentration_mg_ml else None,
        }

def run():
    vdd = VeterinaryDrugDosage(drug_name="Amoxicillin", species=Species.DOG, body_weight_kg=20, standard_dose_mg_kg=10, frequency_per_day=2, duration_days=10)
    print(vdd.stats(concentration_mg_ml=50))

if __name__ == "__main__":
    run()
