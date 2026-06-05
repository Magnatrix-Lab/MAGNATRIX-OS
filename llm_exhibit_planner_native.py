"""Exhibit Planner — flow, capacity, dwell time, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Exhibit:
    name: str
    area_sqm: float
    capacity: int
    dwell_minutes: float
    prerequisites: List[str] = field(default_factory=list)

class ExhibitPlanner:
    def __init__(self):
        self.exhibits: List[Exhibit] = []

    def add_exhibit(self, e: Exhibit):
        self.exhibits.append(e)

    def total_capacity(self) -> int:
        return sum(e.capacity for e in self.exhibits)

    def total_dwell_time(self) -> float:
        return sum(e.dwell_minutes for e in self.exhibits)

    def flow_rate(self, visitors_per_hour: int) -> float:
        total_cap = self.total_capacity()
        return visitors_per_hour / total_cap if total_cap > 0 else 0.0

    def bottleneck(self) -> Optional[str]:
        if not self.exhibits:
            return None
        min_cap = min(e.capacity for e in self.exhibits)
        for e in self.exhibits:
            if e.capacity == min_cap:
                return e.name
        return None

    def visitor_journey(self, start: str) -> List[str]:
        visited = set()
        journey = []
        current = start
        while current and current not in visited:
            visited.add(current)
            journey.append(current)
            e = next((x for x in self.exhibits if x.name == current), None)
            if e and e.prerequisites:
                current = e.prerequisites[0]
            else:
                break
        return journey

    def stats(self) -> Dict:
        return {"exhibits": len(self.exhibits), "capacity": self.total_capacity(), "total_dwell_min": self.total_dwell_time(), "bottleneck": self.bottleneck()}

def run():
    ep = ExhibitPlanner()
    ep.add_exhibit(Exhibit("Intro", 50, 30, 5))
    ep.add_exhibit(Exhibit("Main", 200, 50, 20, ["Intro"]))
    ep.add_exhibit(Exhibit("Gift Shop", 30, 10, 10, ["Main"]))
    print(ep.stats())
    print("Journey:", ep.visitor_journey("Intro"))

if __name__ == "__main__":
    run()
