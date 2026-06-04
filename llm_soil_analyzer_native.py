"""Soil Analyzer — texture, pH, NPK, organic matter, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class SoilAnalyzer:
    ph: float = 7.0
    nitrogen: float = 50.0
    phosphorus: float = 30.0
    potassium: float = 200.0
    organic_matter: float = 3.0
    sand: float = 40.0
    silt: float = 40.0
    clay: float = 20.0

    def texture(self) -> str:
        if self.sand > 50:
            return "sandy"
        elif self.clay > 40:
            return "clay"
        elif self.silt > 50:
            return "silty"
        else:
            return "loam"

    def ph_status(self) -> str:
        if self.ph < 5.5:
            return "acidic"
        elif self.ph > 7.5:
            return "alkaline"
        return "neutral"

    def fertility_index(self) -> float:
        return (self.nitrogen / 100 + self.phosphorus / 50 + self.potassium / 300 + self.organic_matter / 5) / 4

    def recommendations(self) -> List[str]:
        recs = []
        if self.ph < 6.0:
            recs.append("Add lime")
        if self.nitrogen < 40:
            recs.append("Add nitrogen fertilizer")
        if self.phosphorus < 20:
            recs.append("Add phosphorus")
        if self.potassium < 150:
            recs.append("Add potassium")
        if self.organic_matter < 2:
            recs.append("Add compost")
        return recs

    def stats(self) -> Dict:
        return {"texture": self.texture(), "ph_status": self.ph_status(), "fertility": round(self.fertility_index(), 3)}

def run():
    sa = SoilAnalyzer(ph=5.2, nitrogen=30, phosphorus=15, organic_matter=1.5)
    print(sa.stats())
    print("Recommendations:", sa.recommendations())

if __name__ == "__main__":
    run()
