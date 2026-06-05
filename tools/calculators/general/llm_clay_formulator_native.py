"""Clay Formulator — plasticity, shrinkage, absorption, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ClayFormulator:
    clay_pct: float = 50.0
    feldspar_pct: float = 25.0
    silica_pct: float = 25.0
    water_pct: float = 20.0

    def total_solids(self) -> float:
        return self.clay_pct + self.feldspar_pct + self.silica_pct

    def plasticity_index(self) -> float:
        return self.clay_pct / self.total_solids() * 100 if self.total_solids() > 0 else 0.0

    def shrinkage(self, dry_shrink: float = 0.06, firing_shrink: float = 0.08) -> float:
        return 1 - (1 - dry_shrink) * (1 - firing_shrink)

    def absorption(self, porosity: float = 0.15) -> float:
        return porosity * 0.8

    def maturation_temp(self, base: float = 1200.0) -> float:
        return base - self.feldspar_pct * 2

    def stats(self) -> Dict:
        return {"plasticity": round(self.plasticity_index(), 1), "shrinkage": round(self.shrinkage(), 3), "maturation": self.maturation_temp()}

def run():
    cf = ClayFormulator(clay_pct=40, feldspar_pct=35, silica_pct=25)
    print(cf.stats())

if __name__ == "__main__":
    run()
