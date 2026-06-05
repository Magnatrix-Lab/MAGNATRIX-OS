"""Stage Designer — rigging, load, sightlines, set pieces, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class StageDesigner:
    rigging_points: int = 4
    max_load_kg_per_point: float = 500.0
    set_pieces: List[Dict] = field(default_factory=list)

    def total_rigging_capacity(self) -> float:
        return self.rigging_points * self.max_load_kg_per_point

    def set_weight(self) -> float:
        return sum(p.get("weight_kg", 0) for p in self.set_pieces)

    def safety_factor(self) -> float:
        return self.total_rigging_capacity() / self.set_weight() if self.set_weight() > 0 else float("inf")

    def stats(self) -> Dict:
        return {"capacity_kg": self.total_rigging_capacity(), "set_weight_kg": round(self.set_weight(), 2), "safety_factor": round(self.safety_factor(), 2)}

def run():
    sd = StageDesigner(rigging_points=6, set_pieces=[{"weight_kg": 150}, {"weight_kg": 80}, {"weight_kg": 200}])
    print(sd.stats())

if __name__ == "__main__":
    run()
