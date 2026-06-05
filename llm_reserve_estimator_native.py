"""Reserve Estimator — tonnage, volume, confidence, JORC, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ReserveEstimator:
    area_sqm: float = 10000.0
    thickness_m: float = 5.0
    density: float = 2.5
    grade: float = 1.0

    def in_situ_tonnage(self) -> float:
        return self.area_sqm * self.thickness_m * self.density

    def contained_metal(self) -> float:
        return self.in_situ_tonnage() * (self.grade / 100)

    def confidence_category(self, drill_density: float) -> str:
        if drill_density < 50: return "inferred"
        elif drill_density < 100: return "indicated"
        return "measured"

    def strip_adjusted(self, strip_ratio: float) -> float:
        return self.in_situ_tonnage() / (1 + strip_ratio)

    def mineable_ratio(self, dilution: float = 0.1, recovery: float = 0.85) -> float:
        return (1 - dilution) * recovery

    def stats(self) -> Dict:
        return {"tonnage": round(self.in_situ_tonnage(), 0), "metal": round(self.contained_metal(), 1), "confidence": self.confidence_category(75)}

def run():
    re = ReserveEstimator(area_sqm=50000, thickness_m=8, density=2.7, grade=2.5)
    print(re.stats())
    print("Mineable ratio:", re.mineable_ratio())

if __name__ == "__main__":
    run()
