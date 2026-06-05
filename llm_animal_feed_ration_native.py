"""Native stdlib module: Animal Feed Ration Calculator
Calculates feed rations by animal type, weight, and production stage.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class ProductionStage(Enum):
    MAINTENANCE = "maintenance"
    GROWTH = "growth"
    LACTATION = "lactation"
    GESTATION = "gestation"
    WORK = "work"

class AnimalType(Enum):
    DAIRY_COW = "dairy_cow"
    BEEF_COW = "beef_cow"
    HORSE = "horse"
    PIG = "pig"
    SHEEP = "sheep"
    POULTRY = "poultry"

@dataclass
class AnimalFeedRation:
    animal_type: AnimalType
    body_weight_kg: float
    production_stage: ProductionStage
    milk_yield_kg_day: float = 0.0
    work_hours_day: float = 0.0

    def maintenance_requirement_mcal_day(self) -> float:
        base = {AnimalType.DAIRY_COW: 0.07, AnimalType.BEEF_COW: 0.065, AnimalType.HORSE: 0.036, AnimalType.PIG: 0.055, AnimalType.SHEEP: 0.06, AnimalType.POULTRY: 0.15}
        return self.body_weight_kg ** 0.75 * base.get(self.animal_type, 0.06)

    def production_requirement_mcal_day(self) -> float:
        if self.production_stage == ProductionStage.LACTATION and self.animal_type == AnimalType.DAIRY_COW:
            return self.milk_yield_kg_day * 0.74
        elif self.production_stage == ProductionStage.WORK and self.animal_type == AnimalType.HORSE:
            return self.work_hours_day * 0.5
        elif self.production_stage == ProductionStage.GROWTH:
            return self.maintenance_requirement_mcal_day() * 0.2
        elif self.production_stage == ProductionStage.GESTATION:
            return self.maintenance_requirement_mcal_day() * 0.15
        return 0.0

    def total_energy_mcal_day(self) -> float:
        return self.maintenance_requirement_mcal_day() + self.production_requirement_mcal_day()

    def dry_matter_intake_kg_day(self) -> float:
        return self.body_weight_kg ** 0.75 * 0.03

    def protein_requirement_pct(self) -> float:
        stages = {ProductionStage.MAINTENANCE: 10, ProductionStage.GROWTH: 14, ProductionStage.LACTATION: 16, ProductionStage.GESTATION: 12, ProductionStage.WORK: 12}
        return stages.get(self.production_stage, 12)

    def stats(self) -> Dict:
        return {
            "animal": self.animal_type.value,
            "stage": self.production_stage.value,
            "weight_kg": self.body_weight_kg,
            "maintenance_mcal": round(self.maintenance_requirement_mcal_day(), 2),
            "production_mcal": round(self.production_requirement_mcal_day(), 2),
            "total_energy_mcal": round(self.total_energy_mcal_day(), 2),
            "dmi_kg_day": round(self.dry_matter_intake_kg_day(), 2),
            "protein_pct": self.protein_requirement_pct(),
        }

def run():
    afr = AnimalFeedRation(animal_type=AnimalType.DAIRY_COW, body_weight_kg=600, production_stage=ProductionStage.LACTATION, milk_yield_kg_day=30)
    print(afr.stats())

if __name__ == "__main__":
    run()
