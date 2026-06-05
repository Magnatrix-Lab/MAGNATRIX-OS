"""Native stdlib module: Soil Analyzer
Calculates soil composition, pH balance, and amendment recommendations.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class SoilType(Enum):
    SANDY = "sandy"
    CLAY = "clay"
    SILT = "silt"
    LOAM = "loam"
    PEAT = "peat"

@dataclass
class SoilAnalyzer:
    ph: float
    nitrogen_ppm: float
    phosphorus_ppm: float
    potassium_ppm: float
    organic_matter_pct: float
    soil_type: SoilType

    def npk_ratio(self) -> str:
        total = self.nitrogen_ppm + self.phosphorus_ppm + self.potassium_ppm
        if total == 0:
            return "0:0:0"
        n = int((self.nitrogen_ppm / total) * 100)
        p = int((self.phosphorus_ppm / total) * 100)
        k = int((self.potassium_ppm / total) * 100)
        return f"{n}:{p}:{k}"

    def ph_status(self) -> str:
        if self.ph < 6.0:
            return "acidic"
        elif self.ph > 7.5:
            return "alkaline"
        return "neutral"

    def amendment_needed(self) -> List[str]:
        needs = []
        if self.ph < 6.0:
            needs.append("lime")
        if self.ph > 7.5:
            needs.append("sulfur")
        if self.nitrogen_ppm < 20:
            needs.append("nitrogen fertilizer")
        if self.phosphorus_ppm < 15:
            needs.append("phosphorus fertilizer")
        if self.potassium_ppm < 100:
            needs.append("potassium fertilizer")
        if self.organic_matter_pct < 3:
            needs.append("compost")
        return needs

    def stats(self) -> Dict:
        return {
            "ph": self.ph,
            "ph_status": self.ph_status(),
            "npk_ratio": self.npk_ratio(),
            "organic_matter_pct": self.organic_matter_pct,
            "amendments": self.amendment_needed(),
            "soil_type": self.soil_type.value,
        }

def run():
    sa = SoilAnalyzer(ph=6.2, nitrogen_ppm=25, phosphorus_ppm=12, potassium_ppm=150, organic_matter_pct=4.5, soil_type=SoilType.LOAM)
    print(sa.stats())

if __name__ == "__main__":
    run()
