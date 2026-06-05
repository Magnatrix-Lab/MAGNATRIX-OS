"""Native stdlib module: Essential Oil Extractor
Estimates essential oil yield by plant material, method, and extraction efficiency.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class ExtractionMethod(Enum):
    STEAM_DISTILLATION = "steam_distillation"
    COLD_PRESS = "cold_press"
    SOLVENT = "solvent"
    CO2 = "co2"

@dataclass
class EssentialOilExtractor:
    plant_material_kg: float
    material_name: str
    method: ExtractionMethod
    typical_yield_pct: float
    efficiency_factor: float = 0.85

    def oil_yield_ml(self) -> float:
        return self.plant_material_kg * 1000 * (self.typical_yield_pct / 100) * self.efficiency_factor

    def oil_yield_g(self) -> float:
        return self.oil_yield_ml() * 0.9

    def stats(self) -> Dict[str, float]:
        return {
            "oil_yield_ml": round(self.oil_yield_ml(), 2),
            "oil_yield_g": round(self.oil_yield_g(), 2),
            "efficiency_pct": self.efficiency_factor * 100,
            "method": self.method.value,
        }

def run():
    eo = EssentialOilExtractor(plant_material_kg=100, material_name="Lavender", method=ExtractionMethod.STEAM_DISTILLATION, typical_yield_pct=0.8)
    print(eo.stats())

if __name__ == "__main__":
    run()
