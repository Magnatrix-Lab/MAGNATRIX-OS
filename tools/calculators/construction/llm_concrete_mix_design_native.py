"""Native stdlib module: Concrete Mix Design Calculator
Calculates concrete mix proportions, water-cement ratio, and strength estimates.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class ExposureClass(Enum):
    XC1 = "xc1"
    XC2 = "xc2"
    XC3 = "xc3"
    XC4 = "xc4"
    XD1 = "xd1"
    XD2 = "xd2"
    XS1 = "xs1"
    XS2 = "xs2"
    XS3 = "xs3"

@dataclass
class ConcreteMixDesignCalculator:
    target_strength_mpa: float
    slump_mm: float
    max_aggregate_size_mm: float
    cement_type: str
    exposure_class: ExposureClass
    water_cement_ratio: float = 0.5

    def required_mean_strength_mpa(self) -> float:
        return self.target_strength_mpa + 1.65 * 5

    def estimated_28day_strength_mpa(self) -> float:
        if self.water_cement_ratio >= 0.7:
            return 30 / self.water_cement_ratio
        return 35 / self.water_cement_ratio

    def water_content_kg_m3(self) -> float:
        if self.max_aggregate_size_mm >= 32:
            return 160 + self.slump_mm / 10
        elif self.max_aggregate_size_mm >= 20:
            return 180 + self.slump_mm / 10
        return 200 + self.slump_mm / 10

    def cement_content_kg_m3(self) -> float:
        if self.water_cement_ratio == 0:
            return 0.0
        return self.water_content_kg_m3() / self.water_cement_ratio

    def coarse_aggregate_kg_m3(self) -> float:
        return 1100 - (self.slump_mm - 50) * 2

    def fine_aggregate_kg_m3(self) -> float:
        total = 2400
        return total - self.cement_content_kg_m3() - self.water_content_kg_m3() - self.coarse_aggregate_kg_m3()

    def air_content_pct(self) -> float:
        if self.max_aggregate_size_mm <= 20:
            return 4.0
        return 2.0

    def stats(self) -> Dict:
        return {
            "target_strength_mpa": self.target_strength_mpa,
            "required_mean_strength": round(self.required_mean_strength_mpa(), 1),
            "estimated_28day_mpa": round(self.estimated_28day_strength_mpa(), 1),
            "water_content_kg_m3": round(self.water_content_kg_m3(), 1),
            "cement_content_kg_m3": round(self.cement_content_kg_m3(), 1),
            "coarse_aggregate_kg_m3": round(self.coarse_aggregate_kg_m3(), 1),
            "fine_aggregate_kg_m3": round(self.fine_aggregate_kg_m3(), 1),
            "water_cement_ratio": self.water_cement_ratio,
        }

def run():
    cmdc = ConcreteMixDesignCalculator(target_strength_mpa=30, slump_mm=100, max_aggregate_size_mm=20, cement_type="OPC", exposure_class=ExposureClass.XC2, water_cement_ratio=0.55)
    print(cmdc.stats())

if __name__ == "__main__":
    run()
