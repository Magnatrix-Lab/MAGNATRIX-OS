"""Tour Optimizer — attractions, time windows, travel, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Attraction:
    name: str
    x: float
    y: float
    duration: float
    open_time: float
    close_time: float
    rating: float

class TourOptimizer:
    def __init__(self):
        self.attractions: List[Attraction] = []

    def add_attraction(self, a: Attraction):
        self.attractions.append(a)

    def travel_time(self, a: Attraction, b: Attraction) -> float:
        d = math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)
        return d * 2

    def feasible_order(self, start_time: float = 9.0) -> List[Attraction]:
        sorted_attr = sorted(self.attractions, key=lambda a: a.close_time)
        route = []
        current_time = start_time
        current = None
        remaining = list(sorted_attr)
        while remaining:
            found = None
            for a in remaining:
                travel = 0 if current is None else self.travel_time(current, a)
                arrival = current_time + travel
                if arrival >= a.open_time and arrival + a.duration <= a.close_time:
                    found = a
                    break
            if not found:
                break
            route.append(found)
            current_time = max(current_time + (0 if current is None else self.travel_time(current, found)), found.open_time) + found.duration
            current = found
            remaining.remove(found)
        return route

    def total_rating(self, route: List[Attraction]) -> float:
        return sum(a.rating for a in route)

    def stats(self) -> Dict:
        route = self.feasible_order()
        return {"attractions": len(self.attractions), "route_length": len(route), "total_rating": round(self.total_rating(route), 1)}

def run():
    to = TourOptimizer()
    to.add_attraction(Attraction("Museum", 0, 0, 2, 9, 17, 4.5))
    to.add_attraction(Attraction("Park", 2, 1, 1, 6, 20, 4.0))
    to.add_attraction(Attraction("Tower", 3, 3, 3, 10, 18, 4.8))
    print(to.stats())
    print("Route:", [a.name for a in to.feasible_order()])

if __name__ == "__main__":
    run()
