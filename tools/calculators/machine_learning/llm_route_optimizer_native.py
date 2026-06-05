"""Route Optimizer — TSP, nearest neighbor, sweep, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math, random

@dataclass
class RouteOptimizer:
    locations: List[Tuple[float, float]] = field(default_factory=list)

    def distance(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

    def nearest_neighbor(self) -> List[int]:
        if not self.locations:
            return []
        n = len(self.locations)
        visited = [False] * n
        route = [0]
        visited[0] = True
        for _ in range(n - 1):
            last = route[-1]
            nearest = -1
            min_dist = float('inf')
            for i in range(n):
                if not visited[i]:
                    d = self.distance(self.locations[last], self.locations[i])
                    if d < min_dist:
                        min_dist = d
                        nearest = i
            route.append(nearest)
            visited[nearest] = True
        return route

    def total_distance(self, route: List[int]) -> float:
        return sum(self.distance(self.locations[route[i]], self.locations[route[(i+1)%len(route)]]) for i in range(len(route)))

    def two_opt(self, route: List[int]) -> List[int]:
        improved = True
        best = list(route)
        while improved:
            improved = False
            for i in range(1, len(best) - 1):
                for j in range(i + 1, len(best)):
                    new_route = best[:i] + best[i:j][::-1] + best[j:]
                    if self.total_distance(new_route) < self.total_distance(best):
                        best = new_route
                        improved = True
        return best

    def stats(self, route: List[int]) -> Dict:
        return {"stops": len(route), "total_dist": round(self.total_distance(route), 2)}

def run():
    ro = RouteOptimizer(locations=[(0,0),(2,3),(5,2),(3,6),(1,5)])
    route = ro.nearest_neighbor()
    print("NN route:", route, "dist:", ro.total_distance(route))
    opt = ro.two_opt(route)
    print("2-opt:", opt, "dist:", ro.total_distance(opt))
    print(ro.stats(opt))

if __name__ == "__main__":
    run()
