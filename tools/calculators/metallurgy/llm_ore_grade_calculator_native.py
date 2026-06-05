"""Ore Grade Calculator — assay, cut-off, dilution, recovery, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class OreGradeCalculator:
    assays: List[float] = field(default_factory=list)
    cut_off: float = 0.5
    tonnage: float = 100000.0

    def average_grade(self) -> float:
        return sum(self.assays) / len(self.assays) if self.assays else 0.0

    def above_cutoff(self) -> List[float]:
        return [a for a in self.assays if a >= self.cut_off]

    def diluted_grade(self, dilution_pct: float = 0.1) -> float:
        avg = self.average_grade()
        return avg * (1 - dilution_pct) if dilution_pct < 1 else 0.0

    def recovered_metal(self, recovery_pct: float = 0.85) -> float:
        return self.tonnage * self.average_grade() * recovery_pct

    def strip_ratio(self, waste_tons: float) -> float:
        return waste_tons / self.tonnage if self.tonnage > 0 else 0.0

    def stats(self) -> Dict:
        return {"avg_grade": round(self.average_grade(), 3), "above_cutoff": len(self.above_cutoff()), "recovered": round(self.recovered_metal(), 0)}

def run():
    ogc = OreGradeCalculator(assays=[1.2, 0.8, 0.3, 2.1, 0.6, 1.5], cut_off=0.5, tonnage=50000)
    print(ogc.stats())
    print("Diluted:", ogc.diluted_grade(0.15))
    print("Strip ratio:", ogc.strip_ratio(100000))

if __name__ == "__main__":
    run()
