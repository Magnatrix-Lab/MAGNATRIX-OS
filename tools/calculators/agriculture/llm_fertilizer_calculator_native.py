"""Native stdlib module: Fertilizer Calculator
Calculates fertilizer application rates and nutrient delivery.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class FertilizerCalculator:
    fertilizer_name: str
    n_pct: float
    p_pct: float
    k_pct: float
    application_rate_kg_per_ha: float
    area_ha: float

    def total_fertilizer_kg(self) -> float:
        return self.application_rate_kg_per_ha * self.area_ha

    def nitrogen_kg(self) -> float:
        return self.total_fertilizer_kg() * (self.n_pct / 100)

    def phosphorus_kg(self) -> float:
        return self.total_fertilizer_kg() * (self.p_pct / 100)

    def potassium_kg(self) -> float:
        return self.total_fertilizer_kg() * (self.k_pct / 100)

    def nutrient_kg(self) -> float:
        return self.nitrogen_kg() + self.phosphorus_kg() + self.potassium_kg()

    def stats(self) -> Dict:
        return {
            "fertilizer": self.fertilizer_name,
            "npk": f"{self.n_pct}-{self.p_pct}-{self.k_pct}",
            "total_kg": round(self.total_fertilizer_kg(), 1),
            "nitrogen_kg": round(self.nitrogen_kg(), 1),
            "phosphorus_kg": round(self.phosphorus_kg(), 1),
            "potassium_kg": round(self.potassium_kg(), 1),
        }

def run():
    fc = FertilizerCalculator(fertilizer_name="NPK 15-15-15", n_pct=15, p_pct=15, k_pct=15, application_rate_kg_per_ha=200, area_ha=25)
    print(fc.stats())

if __name__ == "__main__":
    run()
