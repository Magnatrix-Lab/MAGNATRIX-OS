"""Flight Planner — route, fuel, waypoints, ETAs, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Waypoint:
    name: str
    lat: float
    lon: float
    alt: float = 0.0

class FlightPlanner:
    def __init__(self):
        self.waypoints: List[Waypoint] = []
        self.cruise_speed: float = 450.0

    def add_waypoint(self, wp: Waypoint):
        self.waypoints.append(wp)

    def leg_distance(self, a: Waypoint, b: Waypoint) -> float:
        R = 6371.0
        dlat = math.radians(b.lat - a.lat)
        dlon = math.radians(b.lon - a.lon)
        ha = math.sin(dlat/2)**2 + math.cos(math.radians(a.lat)) * math.cos(math.radians(b.lat)) * math.sin(dlon/2)**2
        return 2 * R * math.asin(min(1, math.sqrt(ha)))

    def total_distance(self) -> float:
        return sum(self.leg_distance(self.waypoints[i], self.waypoints[i+1]) for i in range(len(self.waypoints)-1))

    def flight_time(self) -> float:
        return self.total_distance() / self.cruise_speed if self.cruise_speed > 0 else 0.0

    def fuel_required(self, burn_rate: float = 3000.0) -> float:
        return self.flight_time() * burn_rate

    def etas(self, departure: float = 0.0) -> List[Tuple[str, float]]:
        times = []
        t = departure
        for i in range(len(self.waypoints)):
            times.append((self.waypoints[i].name, t))
            if i < len(self.waypoints) - 1:
                t += self.leg_distance(self.waypoints[i], self.waypoints[i+1]) / self.cruise_speed
        return times

    def stats(self) -> Dict:
        return {"waypoints": len(self.waypoints), "distance": round(self.total_distance(), 1), "flight_time": round(self.flight_time(), 2)}

def run():
    fp = FlightPlanner()
    fp.add_waypoint(Waypoint("JFK", 40.64, -73.78))
    fp.add_waypoint(Waypoint("BOS", 42.37, -71.02))
    fp.add_waypoint(Waypoint("DCA", 38.85, -77.04))
    print(fp.stats())
    print("ETAs:", fp.etas())

if __name__ == "__main__":
    run()
