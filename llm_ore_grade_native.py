"""Ore Grade Calculator — assay, cutoff, dilution, recovery, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class OreGrade:
    assays: List[float] = field(default_factory=list)
    cutoff: float = 0.5
    dilution: float = 0.1
    recovery: float = 0.85

    def average_grade(self) -> float:
        return sum(self.assays) / len(self.assays) if self.assays else 0.0

    def diluted_grade(self) -> float:
        return self.average_grade() * (1 - self.dilution)

    def recovered_metal(self, tonnage: float) -> float:
        return tonnage * self.diluted_grade() * self.recovery

    def strip_ratio(self, waste: float, ore: float) -> float:
        return waste / ore if ore > 0 else 0.0

    def above_cutoff(self) -> List[float]:
        return [a for a in self.assays if a >= self.cutoff]

    def stats(self, tonnage: float = 1000) -> Dict:
        return {"avg_grade": round(self.average_grade(), 3), "diluted": round(self.diluted_grade(), 3), "recovered": round(self.recovered_metal(tonnage), 1)}

def run():
    og = OreGrade([1.2, 0.8, 0.3, 1.5, 0.6], cutoff=0.5, dilution=0.1, recovery=0.85)
    print(og.stats())
    print("Above cutoff:", og.above_cutoff())

if __name__ == "__main__":
    run()
