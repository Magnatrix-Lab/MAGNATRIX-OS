"""Native stdlib module: Plastic Recycling Calculator
Calculates recycling yields, contamination levels, and regrind ratios.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class PlasticType(Enum):
    PET = "pet"
    HDPE = "hdpe"
    PVC = "pvc"
    LDPE = "ldpe"
    PP = "pp"
    PS = "ps"
    ABS = "abs"
    PC = "pc"

@dataclass
class PlasticRecyclingCalculator:
    plastic_type: PlasticType
    input_weight_kg: float
    contamination_pct: float
    moisture_pct: float
    regrind_ratio_pct: float
    degradation_cycles: int = 1

    def usable_weight_kg(self) -> float:
        return self.input_weight_kg * (1 - (self.contamination_pct + self.moisture_pct) / 100)

    def yield_pct(self) -> float:
        if self.input_weight_kg == 0:
            return 0.0
        return (self.usable_weight_kg() / self.input_weight_kg) * 100

    def regrind_weight_kg(self) -> float:
        return self.usable_weight_kg() * (self.regrind_ratio_pct / 100)

    def virgin_weight_kg(self) -> float:
        return self.usable_weight_kg() * (1 - self.regrind_ratio_pct / 100)

    def property_retention_pct(self) -> float:
        base = 100 - self.degradation_cycles * 5
        if self.regrind_ratio_pct > 50:
            base -= 10
        return max(60, base)

    def melt_index_change_pct(self) -> float:
        return self.degradation_cycles * 10

    def processing_energy_kwh_kg(self) -> float:
        base = 0.5
        if self.contamination_pct > 5:
            base += 0.2
        return base

    def stats(self) -> Dict:
        return {
            "plastic_type": self.plastic_type.value,
            "usable_weight_kg": round(self.usable_weight_kg(), 1),
            "yield_pct": round(self.yield_pct(), 1),
            "regrind_kg": round(self.regrind_weight_kg(), 1),
            "virgin_kg": round(self.virgin_weight_kg(), 1),
            "property_retention_pct": self.property_retention_pct(),
            "melt_index_change_pct": self.melt_index_change_pct(),
            "processing_energy_kwh_kg": self.processing_energy_kwh_kg(),
        }

def run():
    prc = PlasticRecyclingCalculator(plastic_type=PlasticType.PET, input_weight_kg=1000, contamination_pct=3, moisture_pct=0.5, regrind_ratio_pct=30, degradation_cycles=2)
    print(prc.stats())

if __name__ == "__main__":
    run()
