"""Logistics Router — VRP, delivery sequence, capacity constraint, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math
import random

@dataclass
class DeliveryPoint:
    point_id: str
    x: float
    y: float
    demand: float
    time_window: Tuple[float, float]

class LogisticsRouter:
    def __init__(self, vehicle_capacity: float = 100):
        self.vehicle_capacity = vehicle_capacity
        self.depot = (0.0, 0.0)
        self.points: List[DeliveryPoint] = []
        self.routes: List[List[str]] = []
        self.distances: Dict[Tuple[str, str], float] = {}

    def add_point(self, point: DeliveryPoint):
        self.points.append(point)

    def _distance(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

    def build_distance_matrix(self):
        all_points = [("depot", self.depot[0], self.depot[1])] + [(p.point_id, p.x, p.y) for p in self.points]
        for i, (id1, x1, y1) in enumerate(all_points):
            for j, (id2, x2, y2) in enumerate(all_points):
                self.distances[(id1, id2)] = self._distance((x1, y1), (x2, y2))

    def solve_vrp(self) -> List[List[str]]:
        self.build_distance_matrix()
        self.routes = []
        unvisited = set(p.point_id for p in self.points)
        while unvisited:
            route = []
            capacity = self.vehicle_capacity
            current = "depot"
            while unvisited:
                candidates = [pid for pid in unvisited if next(p.demand for p in self.points if p.point_id == pid) <= capacity]
                if not candidates:
                    break
                nearest = min(candidates, key=lambda pid: self.distances[(current, pid)])
                demand = next(p.demand for p in self.points if p.point_id == nearest)
                capacity -= demand
                route.append(nearest)
                unvisited.remove(nearest)
                current = nearest
            self.routes.append(route)
        return self.routes

    def route_distance(self, route: List[str]) -> float:
        total = self.distances[("depot", route[0])] if route else 0
        for i in range(len(route) - 1):
            total += self.distances[(route[i], route[i+1])]
        if route:
            total += self.distances[(route[-1], "depot")]
        return total

    def stats(self) -> Dict:
        total_dist = sum(self.route_distance(r) for r in self.routes)
        return {"points": len(self.points), "routes": len(self.routes), "total_distance": total_dist}

def run():
    router = LogisticsRouter(50)
    for i in range(8):
        router.add_point(DeliveryPoint(f"P{i}", random.uniform(0, 50), random.uniform(0, 50), random.uniform(5, 15), (8, 17)))
    routes = router.solve_vrp()
    print("Routes:", routes)
    print(router.stats())

if __name__ == "__main__":
    run()
