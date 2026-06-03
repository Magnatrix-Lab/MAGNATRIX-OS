"""LLM Geo Locator — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

@dataclass
class GeoPoint:
    lat: float
    lon: float
    altitude: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class GeoLocator:
    def __init__(self) -> None:
        self._points: Dict[str, GeoPoint] = {}

    def add_point(self, point_id: str, point: GeoPoint) -> None:
        self._points[point_id] = point

    def haversine_distance(self, p1: GeoPoint, p2: GeoPoint) -> float:
        R = 6371000
        lat1, lon1 = math.radians(p1.lat), math.radians(p1.lon)
        lat2, lon2 = math.radians(p2.lat), math.radians(p2.lon)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    def distance_between(self, id1: str, id2: str) -> Optional[float]:
        p1 = self._points.get(id1)
        p2 = self._points.get(id2)
        if not p1 or not p2:
            return None
        return self.haversine_distance(p1, p2)

    def find_nearby(self, center_id: str, radius_km: float) -> List[str]:
        center = self._points.get(center_id)
        if not center:
            return []
        nearby = []
        for pid, point in self._points.items():
            if pid != center_id:
                dist = self.haversine_distance(center, point)
                if dist <= radius_km * 1000:
                    nearby.append(pid)
        return nearby

    def bounding_box(self, points: List[str]) -> Optional[Tuple[float, float, float, float]]:
        selected = [self._points[p] for p in points if p in self._points]
        if not selected:
            return None
        lats = [p.lat for p in selected]
        lons = [p.lon for p in selected]
        return (min(lats), min(lons), max(lats), max(lons))

    def get_stats(self) -> Dict[str, Any]:
        return {"points": len(self._points)}

def run() -> None:
    print("Geo Locator test")
    e = GeoLocator()
    e.add_point("jakarta", GeoPoint(-6.2088, 106.8456))
    e.add_point("bandung", GeoPoint(-6.9175, 107.6191))
    e.add_point("surabaya", GeoPoint(-7.2575, 112.7521))
    print("  Jakarta-Bandung: " + str(e.distance_between("jakarta", "bandung") / 1000) + " km")
    print("  Nearby Jakarta (200km): " + str(e.find_nearby("jakarta", 200)))
    print("  Bounding box: " + str(e.bounding_box(["jakarta", "bandung", "surabaya"])))
    print("  Stats: " + str(e.get_stats()))
    print("Geo Locator test complete.")

if __name__ == "__main__":
    run()
