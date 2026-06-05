"""Dispatch Optimizer — closest unit, priority, ETA, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math, heapq

@dataclass
class Unit:
    id: str
    x: float
    y: float
    status: str
    type: str

@dataclass
class Incident:
    id: str
    x: float
    y: float
    priority: int
    type: str

class DispatchOptimizer:
    def __init__(self):
        self.units: List[Unit] = []
        self.incidents: List[Incident] = []

    def add_unit(self, u: Unit):
        self.units.append(u)

    def add_incident(self, i: Incident):
        self.incidents.append(i)

    def distance(self, a: Unit, b: Incident) -> float:
        return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

    def eta(self, unit: Unit, incident: Incident, speed: float = 60.0) -> float:
        return self.distance(unit, incident) / speed * 60

    def closest_available(self, incident: Incident) -> Optional[Unit]:
        available = [u for u in self.units if u.status == "available" and u.type == incident.type]
        if not available:
            return None
        return min(available, key=lambda u: self.distance(u, incident))

    def dispatch_all(self) -> List[Tuple[str, str, float]]:
        assignments = []
        unassigned_incidents = sorted(self.incidents, key=lambda i: i.priority)
        available_units = [u for u in self.units if u.status == "available"]
        for incident in unassigned_incidents:
            best = None
            best_dist = float('inf')
            for unit in available_units:
                if unit.type == incident.type:
                    d = self.distance(unit, incident)
                    if d < best_dist:
                        best_dist = d
                        best = unit
            if best:
                assignments.append((incident.id, best.id, self.eta(best, incident)))
                available_units.remove(best)
        return assignments

    def coverage_area(self, radius: float) -> float:
        positions = [(u.x, u.y) for u in self.units if u.status == "available"]
        if not positions:
            return 0.0
        return math.pi * radius**2 * len(positions)

    def stats(self) -> Dict:
        return {"units": len(self.units), "incidents": len(self.incidents), "available": len([u for u in self.units if u.status == "available"])}

def run():
    do = DispatchOptimizer()
    do.add_unit(Unit("U1", 0, 0, "available", "fire"))
    do.add_unit(Unit("U2", 10, 10, "available", "medical"))
    do.add_incident(Incident("I1", 2, 2, 1, "fire"))
    do.add_incident(Incident("I2", 8, 8, 2, "medical"))
    print(do.stats())
    print("Dispatch:", do.dispatch_all())

if __name__ == "__main__":
    run()
