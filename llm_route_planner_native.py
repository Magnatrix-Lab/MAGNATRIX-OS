"""Native stdlib module: Route Planner
Simple TSP-style distance calculator and route optimizer for delivery points.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math

@dataclass
class Waypoint:
    name: str
    lat: float
    lon: float
    demand: float = 0.0

@dataclass
class RoutePlanner:
    depot: Waypoint
    stops: List[Waypoint] = field(default_factory=list)
    vehicle_capacity: float = 1000.0

    def _haversine(self, a: Waypoint, b: Waypoint) -> float:
        R = 6371.0
        phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
        dphi = math.radians(b.lat - a.lat)
        dlambda = math.radians(b.lon - a.lon)
        h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * R * math.asin(math.sqrt(h))

    def total_distance(self, route: List[Waypoint]) -> float:
        if not route:
            return 0.0
        dist = self._haversine(self.depot, route[0])
        for i in range(len(route) - 1):
            dist += self._haversine(route[i], route[i + 1])
        dist += self._haversine(route[-1], self.depot)
        return dist

    def nearest_neighbor_route(self) -> List[Waypoint]:
        unvisited = self.stops[:]
        route = []
        current = self.depot
        while unvisited:
            nearest = min(unvisited, key=lambda w: self._haversine(current, w))
            route.append(nearest)
            unvisited.remove(nearest)
            current = nearest
        return route

    def total_demand(self) -> float:
        return sum(s.demand for s in self.stops)

    def stats(self) -> Dict:
        route = self.nearest_neighbor_route()
        return {
            "stops": len(self.stops),
            "total_demand": round(self.total_demand(), 2),
            "route_distance_km": round(self.total_distance(route), 2),
            "vehicle_capacity": self.vehicle_capacity,
            "capacity_used_pct": round((self.total_demand() / max(1, self.vehicle_capacity)) * 100, 1),
        }

def run():
    rp = RoutePlanner(
        depot=Waypoint("DC", 40.7128, -74.0060),
        stops=[
            Waypoint("A", 40.7580, -73.9855, 200),
            Waypoint("B", 40.6892, -74.0445, 150),
            Waypoint("C", 40.7489, -73.9680, 300),
            Waypoint("D", 40.7308, -73.9973, 100),
        ],
        vehicle_capacity=1000
    )
    print(rp.stats())

if __name__ == "__main__":
    run()
