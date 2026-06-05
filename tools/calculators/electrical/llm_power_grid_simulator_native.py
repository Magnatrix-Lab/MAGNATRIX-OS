"""Power Grid Simulator — load flow, generation, transmission, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Bus:
    id: int
    p_demand: float = 0.0
    p_gen: float = 0.0
    voltage: float = 1.0

@dataclass
class Line:
    from_bus: int
    to_bus: int
    reactance: float = 0.1
    capacity: float = 100.0

@dataclass
class PowerGrid:
    buses: List[Bus] = field(default_factory=list)
    lines: List[Line] = field(default_factory=list)

    def total_demand(self) -> float:
        return sum(b.p_demand for b in self.buses)

    def total_generation(self) -> float:
        return sum(b.p_gen for b in self.buses)

    def balance(self) -> float:
        return self.total_generation() - self.total_demand()

    def flow_dc(self, line: Line) -> float:
        fb = next((b for b in self.buses if b.id == line.from_bus), None)
        tb = next((b for b in self.buses if b.id == line.to_bus), None)
        if fb and tb and line.reactance > 0:
            return (fb.voltage - tb.voltage) / line.reactance
        return 0.0

    def check_capacity(self) -> List[str]:
        alerts = []
        for line in self.lines:
            f = abs(self.flow_dc(line))
            if f > line.capacity:
                alerts.append(f"Line {line.from_bus}-{line.to_bus} overloaded: {f:.2f}/{line.capacity}")
        return alerts

    def stats(self) -> Dict:
        return {"buses": len(self.buses), "lines": len(self.lines), "demand": self.total_demand(), "gen": self.total_generation(), "balance": self.balance()}

def run():
    grid = PowerGrid([Bus(1,100,0),Bus(2,50,150),Bus(3,80,0)], [Line(1,2,0.1,200),Line(2,3,0.1,200)])
    print(grid.stats())
    print(grid.check_capacity())

if __name__ == "__main__":
    run()
