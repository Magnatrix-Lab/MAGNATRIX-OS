"""Navigation System — bearing, dead reckoning, waypoint, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class NavigationSystem:
    current_lat: float = 0.0
    current_lon: float = 0.0
    heading: float = 0.0
    speed: float = 0.0

    def bearing_to(self, lat: float, lon: float) -> float:
        dlat = math.radians(lat - self.current_lat)
        dlon = math.radians(lon - self.current_lon)
        y = math.sin(dlon) * math.cos(math.radians(lat))
        x = math.cos(math.radians(self.current_lat)) * math.sin(math.radians(lat)) - math.sin(math.radians(self.current_lat)) * math.cos(math.radians(lat)) * math.cos(dlon)
        brng = math.degrees(math.atan2(y, x))
        return (brng + 360) % 360

    def distance_to(self, lat: float, lon: float) -> float:
        R = 6371000
        dlat = math.radians(lat - self.current_lat)
        dlon = math.radians(lon - self.current_lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(self.current_lat)) * math.cos(math.radians(lat)) * math.sin(dlon/2)**2
        return 2 * R * math.asin(min(1, math.sqrt(a)))

    def dead_reckoning(self, time_hours: float) -> Tuple[float, float]:
        d = self.speed * time_hours
        lat_change = d * math.cos(math.radians(self.heading)) / 111320
        lon_change = d * math.sin(math.radians(self.heading)) / (111320 * math.cos(math.radians(self.current_lat)))
        return self.current_lat + lat_change, self.current_lon + lon_change

    def cross_track_error(self, waypoint_a: Tuple[float, float], waypoint_b: Tuple[float, float]) -> float:
        d13 = self.distance_to(waypoint_a[0], waypoint_a[1])
        d12 = math.sqrt((waypoint_b[0]-waypoint_a[0])**2 + (waypoint_b[1]-waypoint_a[1])**2) * 111000
        if d12 == 0:
            return d13
        brng12 = math.radians(self.bearing_to(waypoint_b[0], waypoint_b[1]))
        brng13 = math.radians(self.bearing_to(waypoint_a[0], waypoint_a[1]))
        return abs(math.asin(min(1, math.sin(brng13 - brng12) * d13 / d12)) * 6371000) if d12 > 0 else 0

    def stats(self) -> Dict:
        return {"heading": self.heading, "speed": self.speed, "position": (self.current_lat, self.current_lon)}

def run():
    ns = NavigationSystem(40.7, -74.0, 90, 500)
    print(ns.stats())
    print("Bearing to London:", ns.bearing_to(51.5, -0.1))
    print("DR 1h:", ns.dead_reckoning(1))

if __name__ == "__main__":
    run()
