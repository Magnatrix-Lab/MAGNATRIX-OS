"""Flight Planner — fuel, range, waypoints, wind, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class FlightPlanner:
    range_nm: float = 1000.0
    fuel_capacity: float = 5000.0
    fuel_consumption: float = 50.0
    """gallons per hour"""
    cruise_speed: float = 450.0

    def endurance(self) -> float:
        return self.fuel_capacity / self.fuel_consumption if self.fuel_consumption > 0 else 0.0

    def max_range(self) -> float:
        return self.endurance() * self.cruise_speed

    def fuel_needed(self, distance: float, headwind: float = 0.0) -> float:
        gs = self.cruise_speed - headwind
        time = distance / gs if gs > 0 else float('inf')
        return time * self.fuel_consumption

    def waypoint_distance(self, waypoints: List[Tuple[float, float]]) -> float:
        total = 0.0
        for i in range(len(waypoints) - 1):
            lat1, lon1 = waypoints[i]
            lat2, lon2 = waypoints[i+1]
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            total += 2 * 3440 * math.asin(min(1, math.sqrt(a)))
        return total

    def can_reach(self, distance: float, alternate_nm: float = 100.0) -> bool:
        needed = self.fuel_needed(distance) + self.fuel_needed(alternate_nm) * 1.1
        return needed <= self.fuel_capacity

    def stats(self, distance: float = 500) -> Dict:
        return {
            "endurance_hrs": round(self.endurance(), 1),
            "max_range_nm": round(self.max_range(), 1),
            "fuel_needed": round(self.fuel_needed(distance), 1),
            "can_reach": self.can_reach(distance)
        }

def run():
    fp = FlightPlanner()
    print(fp.stats(800))
    print("Waypoints:", fp.waypoint_distance([(40.7, -74.0), (51.5, -0.1), (48.9, 2.3)]))

if __name__ == "__main__":
    run()
