"""UAV Controller — waypoint, loiter, geofence, RTL, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class UAVController:
    waypoints: List[Tuple[float, float, float]] = field(default_factory=list)
    """lat, lon, alt"""
    max_speed: float = 15.0
    home: Tuple[float, float, float] = (0, 0, 0)
    geofence_radius: float = 1000.0

    def add_waypoint(self, lat: float, lon: float, alt: float):
        self.waypoints.append((lat, lon, alt))

    def distance_3d(self, a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
        horiz = math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2) * 111000
        vert = a[2] - b[2]
        return math.sqrt(horiz**2 + vert**2)

    def mission_length(self) -> float:
        if len(self.waypoints) < 2:
            return 0.0
        return sum(self.distance_3d(self.waypoints[i], self.waypoints[i+1]) for i in range(len(self.waypoints)-1))

    def mission_time(self) -> float:
        return self.mission_length() / self.max_speed if self.max_speed > 0 else 0

    def in_geofence(self, pos: Tuple[float, float]) -> bool:
        home_horiz = math.sqrt((pos[0]-self.home[0])**2 + (pos[1]-self.home[1])**2) * 111000
        return home_horiz <= self.geofence_radius

    def rtl_bearing(self, current: Tuple[float, float]) -> float:
        dlon = math.radians(self.home[1] - current[1])
        y = math.sin(dlon) * math.cos(math.radians(self.home[0]))
        x = math.cos(math.radians(current[0])) * math.sin(math.radians(self.home[0])) - math.sin(math.radians(current[0])) * math.cos(math.radians(self.home[0])) * math.cos(dlon)
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    def loiter_points(self, center: Tuple[float, float], radius: float, n: int = 8) -> List[Tuple[float, float]]:
        points = []
        for i in range(n):
            angle = 2 * math.pi * i / n
            lat = center[0] + (radius * math.cos(angle) / 111000)
            lon = center[1] + (radius * math.sin(angle) / (111000 * math.cos(math.radians(center[0]))))
            points.append((lat, lon))
        return points

    def stats(self) -> Dict:
        return {"waypoints": len(self.waypoints), "mission_km": round(self.mission_length()/1000, 2), "time_min": round(self.mission_time()/60, 1)}

def run():
    uc = UAVController(home=(40.7, -74.0, 0), geofence_radius=500)
    uc.add_waypoint(40.71, -74.01, 100)
    uc.add_waypoint(40.72, -74.02, 100)
    print(uc.stats())
    print("Loiter:", uc.loiter_points((40.7, -74.0), 100)[:3])

if __name__ == "__main__":
    run()
