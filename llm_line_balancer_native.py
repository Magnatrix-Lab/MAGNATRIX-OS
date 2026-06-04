"""Line Balancer — cycle time, workstations, precedence, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

@dataclass
class Task:
    id: str
    time: float
    predecessors: List[str] = field(default_factory=list)

class LineBalancer:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.cycle_time: float = 10.0

    def add_task(self, t: Task):
        self.tasks[t.id] = t

    def total_time(self) -> float:
        return sum(t.time for t in self.tasks.values())

    def min_stations(self) -> int:
        return math.ceil(self.total_time() / self.cycle_time)

    def balance(self) -> List[List[str]]:
        stations = []
        assigned = set()
        while len(assigned) < len(self.tasks):
            station = []
            station_time = 0.0
            available = [t for t in self.tasks.values() if t.id not in assigned and all(p in assigned for p in t.predecessors)]
            available.sort(key=lambda t: t.time, reverse=True)
            for t in available:
                if station_time + t.time <= self.cycle_time:
                    station.append(t.id)
                    station_time += t.time
                    assigned.add(t.id)
            stations.append(station)
        return stations

    def efficiency(self) -> float:
        stations = self.balance()
        idle = sum(self.cycle_time - sum(self.tasks[tid].time for tid in s) for s in stations)
        return 1 - idle / (len(stations) * self.cycle_time)

    def stats(self) -> Dict:
        stations = self.balance()
        return {"tasks": len(self.tasks), "stations": len(stations), "efficiency": round(self.efficiency(), 3)}

def run():
    lb = LineBalancer(cycle_time=10)
    lb.add_task(Task("A", 3))
    lb.add_task(Task("B", 4, ["A"]))
    lb.add_task(Task("C", 5, ["A"]))
    lb.add_task(Task("D", 3, ["B", "C"]))
    print("Balance:", lb.balance())
    print(lb.stats())

if __name__ == "__main__":
    run()
