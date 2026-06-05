"""Route Efficiency — MPG by route, elevation, speed, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class RouteEfficiency:
    distance_km: float = 0.0
    elevation_changes: List[Tuple[float, float]] = field(default_factory=list)
    """(distance_point, elevation_m)"""
    speeds: List[float] = field(default_factory=list)
    base_consumption: float = 7.0
    """L/100km at flat 60km/h"""

    def avg_speed(self) -> float:
        return sum(self.speeds) / len(self.speeds) if self.speeds else 0.0

    def total_elevation_gain(self) -> float:
        gain = 0.0
        for i in range(1, len(self.elevation_changes)):
            diff = self.elevation_changes[i][1] - self.elevation_changes[i-1][1]
            if diff > 0:
                gain += diff
        return gain

    def consumption_estimate(self) -> float:
        base = self.base_consumption
        speed_factor = 1.0
        avg_speed = self.avg_speed()
        if avg_speed > 0:
            speed_factor = 1 + 0.02 * abs(avg_speed - 60) / 10
        elevation_factor = 1 + self.total_elevation_gain() / (self.distance_km * 100) if self.distance_km > 0 else 1.0
        return base * speed_factor * elevation_factor

    def cost_estimate(self, fuel_price: float = 1.5) -> float:
        return self.consumption_estimate() / 100 * self.distance_km * fuel_price

    def co2_estimate(self) -> float:
        return self.consumption_estimate() / 100 * self.distance_km * 2.31

    def time_estimate(self) -> float:
        speed = self.avg_speed()
        return self.distance_km / speed if speed > 0 else 0.0

    def stats(self) -> Dict:
        return {
            "consumption": round(self.consumption_estimate(), 2),
            "cost": round(self.cost_estimate(), 2),
            "co2_kg": round(self.co2_estimate(), 2),
            "time_hrs": round(self.time_estimate(), 2)
        }

def run():
    re = RouteEfficiency(
        distance_km=120,
        elevation_changes=[(0, 100), (30, 150), (60, 300), (90, 200), (120, 100)],
        speeds=[50, 60, 80, 70, 60],
        base_consumption=6.5
    )
    print(re.stats())

if __name__ == "__main__":
    run()
