"""Evacuation Planner — capacity, routes, time, assembly points, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class EvacuationPlanner:
    population: int = 1000
    exits: List[Dict] = field(default_factory=list)
    """Each: {name, capacity, x, y}"""
    assembly_points: List[Dict] = field(default_factory=list)
    """Each: {name, capacity, x, y}"""

    def add_exit(self, name: str, capacity: int, x: float, y: float):
        self.exits.append({"name": name, "capacity": capacity, "x": x, "y": y})

    def add_assembly(self, name: str, capacity: int, x: float, y: float):
        self.assembly_points.append({"name": name, "capacity": capacity, "x": x, "y": y})

    def total_exit_capacity(self) -> int:
        return sum(e["capacity"] for e in self.exits)

    def total_assembly_capacity(self) -> int:
        return sum(a["capacity"] for a in self.assembly_points)

    def evacuation_time(self, flow_rate: float = 1.5) -> float:
        return self.population / (self.total_exit_capacity() * flow_rate) if self.total_exit_capacity() > 0 else float('inf')

    def nearest_exit(self, x: float, y: float) -> str:
        if not self.exits:
            return ""
        return min(self.exits, key=lambda e: math.sqrt((e["x"]-x)**2 + (e["y"]-y)**2))["name"]

    def nearest_assembly(self, x: float, y: float) -> str:
        if not self.assembly_points:
            return ""
        return min(self.assembly_points, key=lambda a: math.sqrt((a["x"]-x)**2 + (a["y"]-y)**2))["name"]

    def capacity_sufficient(self) -> bool:
        return self.total_exit_capacity() >= self.population and self.total_assembly_capacity() >= self.population

    def stats(self) -> Dict:
        return {"population": self.population, "exits": len(self.exits), "assembly": len(self.assembly_points), "capacity_ok": self.capacity_sufficient(), "evac_time_min": round(self.evacuation_time(), 1)}

def run():
    ep = EvacuationPlanner(population=500)
    ep.add_exit("North", 200, 0, 10)
    ep.add_exit("South", 300, 0, -10)
    ep.add_assembly("AP1", 400, 0, 20)
    print(ep.stats())
    print("Nearest exit from (0,0):", ep.nearest_exit(0, 0))

if __name__ == "__main__":
    run()
