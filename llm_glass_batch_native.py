"""Glass Batch — silica, soda, lime, cullet, batch calculation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class GlassBatch:
    silica_target: float = 72.0
    soda_target: float = 14.0
    lime_target: float = 10.0
    alumina_target: float = 2.0
    cullet_pct: float = 20.0

    def batch_weight(self, total_kg: float = 100.0) -> Dict[str, float]:
        effective = total_kg * (1 - self.cullet_pct / 100)
        return {
            "silica_sand": effective * self.silica_target / 100 / 0.99,
            "soda_ash": effective * self.soda_target / 100 / 0.58,
            "limestone": effective * self.lime_target / 100 / 0.56,
            "alumina": effective * self.alumina_target / 100 / 1.0,
            "cullet": total_kg * self.cullet_pct / 100,
        }

    def melting_energy(self) -> float:
        return 2500 + (100 - self.cullet_pct) * 20

    def viscosity_at_temp(self, temp: float) -> float:
        if temp <= 0:
            return float('inf')
        return 10 ** ( -6 + 5000 / temp )

    def working_range(self, upper: float = 1200, lower: float = 900) -> float:
        return upper - lower

    def stats(self, total_kg: float = 100.0) -> Dict:
        return {"batch": self.batch_weight(total_kg), "energy": self.melting_energy(), "working_range": self.working_range()}

def run():
    gb = GlassBatch(cullet_pct=30)
    print(gb.stats())

if __name__ == "__main__":
    run()
