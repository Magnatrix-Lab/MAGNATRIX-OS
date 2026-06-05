"""Native stdlib module: Concrete Admixture Calculator
Calculates admixture dosages, water reduction, and set time adjustments.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class AdmixtureType(Enum):
    PLASTICIZER = "plasticizer"
    SUPERPLASTICIZER = "superplasticizer"
    ACCELERATOR = "accelerator"
    RETARDER = "retarder"
    AIR_ENTRAINER = "air_entrainer"
    WATERPROOFER = "waterproofer"

@dataclass
class ConcreteAdmixtureCalculator:
    admixture_type: AdmixtureType
    cement_content_kg_m3: float
    base_water_kg_m3: float
    dosage_pct_by_cement: float
    slump_before_mm: float

    def admixture_kg_m3(self) -> float:
        return self.cement_content_kg_m3 * (self.dosage_pct_by_cement / 100)

    def water_reduction_pct(self) -> float:
        reductions = {AdmixtureType.PLASTICIZER: 8, AdmixtureType.SUPERPLASTICIZER: 20, AdmixtureType.ACCELERATOR: 0, AdmixtureType.RETARDER: 0, AdmixtureType.AIR_ENTRAINER: 0, AdmixtureType.WATERPROOFER: 5}
        return reductions.get(self.admixture_type, 0)

    def adjusted_water_kg_m3(self) -> float:
        return self.base_water_kg_m3 * (1 - self.water_reduction_pct() / 100)

    def effective_water_cement_ratio(self) -> float:
        if self.cement_content_kg_m3 == 0:
            return 0.0
        return self.adjusted_water_kg_m3() / self.cement_content_kg_m3

    def slump_increase_mm(self) -> float:
        increases = {AdmixtureType.PLASTICIZER: 50, AdmixtureType.SUPERPLASTICIZER: 100, AdmixtureType.ACCELERATOR: 0, AdmixtureType.RETARDER: 0, AdmixtureType.AIR_ENTRAINER: 0, AdmixtureType.WATERPROOFER: 0}
        return increases.get(self.admixture_type, 0)

    def set_time_change_hr(self) -> float:
        changes = {AdmixtureType.ACCELERATOR: -2, AdmixtureType.RETARDER: 4, AdmixtureType.PLASTICIZER: 0, AdmixtureType.SUPERPLASTICIZER: 0, AdmixtureType.AIR_ENTRAINER: 0, AdmixtureType.WATERPROOFER: 0}
        return changes.get(self.admixture_type, 0)

    def stats(self) -> Dict:
        return {
            "admixture": self.admixture_type.value,
            "admixture_kg_m3": round(self.admixture_kg_m3(), 2),
            "water_reduction_pct": self.water_reduction_pct(),
            "adjusted_water_kg_m3": round(self.adjusted_water_kg_m3(), 1),
            "effective_w_c_ratio": round(self.effective_water_cement_ratio(), 3),
            "slump_increase_mm": self.slump_increase_mm(),
            "set_time_change_hr": self.set_time_change_hr(),
        }

def run():
    cac = ConcreteAdmixtureCalculator(admixture_type=AdmixtureType.SUPERPLASTICIZER, cement_content_kg_m3=350, base_water_kg_m3=180, dosage_pct_by_cement=1.5, slump_before_mm=50)
    print(cac.stats())

if __name__ == "__main__":
    run()
