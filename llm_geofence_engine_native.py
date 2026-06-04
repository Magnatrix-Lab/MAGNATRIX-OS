"""Geofence Engine — point-in-polygon, radius, boundary alerts, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Geofence:
    name: str
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    center: Tuple[float, float] = None
    radius: float = 0.0

    def contains(self, point: Tuple[float, float]) -> bool:
        if self.radius > 0 and self.center:
            return self._distance(self.center, point) <= self.radius
        return self._point_in_polygon(point, self.vertices)

    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        R = 6371000
        dlat = math.radians(p2[0] - p1[0])
        dlon = math.radians(p2[1] - p1[1])
        a = math.sin(dlat/2)**2 + math.cos(math.radians(p1[0])) * math.cos(math.radians(p2[0])) * math.sin(dlon/2)**2
        return 2 * R * math.asin(min(1, math.sqrt(a)))

    def _point_in_polygon(self, point: Tuple[float, float], poly: List[Tuple[float, float]]) -> bool:
        x, y = point
        inside = False
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i+1)%n]
            if ((y1 > y) != (y2 > y)) and (x < (x2-x1)*(y-y1)/(y2-y1)+x1):
                inside = not inside
        return inside

    def distance_to_boundary(self, point: Tuple[float, float]) -> float:
        if self.center:
            return max(0, self._distance(self.center, point) - self.radius)
        return min(self._distance(point, v) for v in self.vertices)

    def stats(self) -> Dict:
        return {"name": self.name, "type": "radius" if self.radius > 0 else "polygon", "vertices": len(self.vertices)}

def run():
    gf = Geofence("ZoneA", center=(40.7, -74.0), radius=1000)
    print("Inside:", gf.contains((40.71, -74.0)))
    gf2 = Geofence("ZoneB", vertices=[(0,0),(0,1),(1,1),(1,0)])
    print("Inside poly:", gf2.contains((0.5, 0.5)))
    print(gf.stats())

if __name__ == "__main__":
    run()
