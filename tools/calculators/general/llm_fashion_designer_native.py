"""Fashion Designer — silhouette, fabric consumption, sizing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class FashionDesigner:
    garment_type: str = "shirt"
    fabric_width_m: float = 1.45

    def fabric_required(self, pattern_area_m2: float = 2.0) -> float:
        return pattern_area_m2 / self.fabric_width_m if self.fabric_width_m > 0 else 0.0

    def cost_per_unit(self, fabric_cost_per_m: float = 5.0, labor: float = 10.0) -> float:
        return self.fabric_required() * fabric_cost_per_m + labor

    def size_ratio(self, measurements: List[float]) -> float:
        if not measurements or measurements[0] == 0:
            return 1.0
        return max(measurements) / measurements[0]

    def stats(self) -> Dict:
        return {"fabric_m": round(self.fabric_required(), 2), "cost_usd": round(self.cost_per_unit(), 2)}

def run():
    fd = FashionDesigner(garment_type="dress", fabric_width_m=1.5)
    print(fd.stats())

if __name__ == "__main__":
    run()
