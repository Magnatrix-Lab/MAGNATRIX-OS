"""Flight Planner — fuel, waypoints, wind, time, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class FlightPlanner:
    waypoints: List[Tuple[float, float]] = field(default_factory=list)
    """lat, lon"""
    cruise_speed: float = 450.0
    fuel_rate: float = 800.0

    def leg_distance(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        R = 6371
        dlat = math.radians(b[0] - a[0])
        dlon = math.radians(b[1] - a[1])
        ha = math.sin(dlat/2)**2 + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlon/2)**2
        return 2 * R * math.asin(min(1, math.sqrt(ha)))

    def total_distance(self) -> float:
        return sum(self.leg_distance(self.waypoints[i], self.waypoints[i+1]) for i in range(len(self.waypoints)-1))

    def flight_time(self) -> float:
        return self.total_distance() / self.cruise_speed if self.cruise_speed > 0 else 0

    def fuel_needed(self, reserve_pct: float = 0.1) -> float:
        base = self.flight_time() * self.fuel_rate
        return base * (1 + reserve_pct)

    def wind_adjusted_time(self, wind_kmh: float, wind_direction: float, track_direction: float) -> float:
        headwind = wind_kmh * math.cos(math.radians(wind_direction - track_direction))
        gs = self.cruise_speed - headwind
        return self.total_distance() / gs if gs > 0 else float('inf')

    def stats(self) -> Dict:
        return {"distance_km": round(self.total_distance(), 1), "time_h": round(self.flight_time(), 2), "fuel_kg": round(self.fuel_needed(), 1)}

def run():
    fp = FlightPlanner(waypoints=[(40.7,-74.0),(51.5,-0.1),(48.9,2.3)], cruise_speed=800, fuel_rate=2500)
    print(fp.stats())

if __name__ == "__main__":
    run()
