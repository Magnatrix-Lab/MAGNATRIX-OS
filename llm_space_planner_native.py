"""Space Planner — circulation, adjacency, zoning, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class SpacePlanner:
    total_area_m2: float = 100.0
    zones: List[Dict] = field(default_factory=list)

    def allocate(self) -> List[Dict]:
        if not self.zones:
            return []
        base = self.total_area_m2 / sum(z.get("ratio", 1) for z in self.zones)
        return [{"name": z["name"], "area_m2": round(z.get("ratio", 1) * base, 2)} for z in self.zones]

    def circulation_factor(self) -> float:
        return self.total_area_m2 * 0.25

    def usable_area(self) -> float:
        return self.total_area_m2 - self.circulation_factor()

    def stats(self) -> Dict:
        return {"allocated": self.allocate(), "circulation_m2": round(self.circulation_factor(), 2), "usable_m2": round(self.usable_area(), 2)}

def run():
    sp = SpacePlanner(total_area_m2=200, zones=[{"name": "Living", "ratio": 3}, {"name": "Kitchen", "ratio": 2}])
    print(sp.stats())

if __name__ == "__main__":
    run()
