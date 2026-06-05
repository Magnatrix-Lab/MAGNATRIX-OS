"""Traffic Optimizer — congestion, signal timing, throughput, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Intersection:
    id: str
    green_time: float = 30.0
    yellow_time: float = 5.0
    red_time: float = 30.0
    arrival_rate: float = 30.0
    """vehicles per minute"""

class TrafficOptimizer:
    def __init__(self):
        self.intersections: List[Intersection] = []

    def add_intersection(self, i: Intersection):
        self.intersections.append(i)

    def cycle_time(self, i: Intersection) -> float:
        return i.green_time + i.yellow_time + i.red_time

    def capacity(self, i: Intersection) -> float:
        cycle = self.cycle_time(i)
        return (i.green_time / cycle) * 60 if cycle > 0 else 0.0

    def saturation(self, i: Intersection) -> float:
        cap = self.capacity(i)
        return i.arrival_rate / cap if cap > 0 else 0.0

    def optimal_green(self, i: Intersection, target_saturation: float = 0.85) -> float:
        if target_saturation <= 0:
            return i.green_time
        needed = i.arrival_rate / target_saturation
        cycle = i.yellow_time + i.red_time + i.green_time
        return needed * cycle / (60 - needed) if needed < 60 else i.green_time

    def total_delay(self, i: Intersection) -> float:
        v = i.arrival_rate
        c = self.capacity(i)
        x = v / c if c > 0 else 0
        if x < 1:
            return (x ** 2) / (2 * v * (1 - x)) if v > 0 and x < 1 else 0.0
        return float('inf')

    def stats(self) -> Dict:
        total_delay = sum(self.total_delay(i) for i in self.intersections)
        return {"intersections": len(self.intersections), "total_delay": round(total_delay, 2)}

def run():
    to = TrafficOptimizer()
    to.add_intersection(Intersection("A", 30, 5, 30, 25))
    to.add_intersection(Intersection("B", 25, 5, 35, 40))
    print(to.stats())
    for i in to.intersections:
        print(f"{i.id}: sat={to.saturation(i):.2f} cap={to.capacity(i):.1f}")

if __name__ == "__main__":
    run()
