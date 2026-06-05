"""Native stdlib module: Elevation Profile Calculator
Calculates elevation gain, loss, and slope from point data.
"""
from dataclasses import dataclass, field
from typing import List, Dict
import math

@dataclass
class ElevationPoint:
    distance_km: float
    elevation_m: float

@dataclass
class ElevationProfileCalculator:
    route_name: str
    points: List[ElevationPoint] = field(default_factory=list)

    def total_elevation_gain_m(self) -> float:
        gain = 0.0
        for i in range(1, len(self.points)):
            diff = self.points[i].elevation_m - self.points[i-1].elevation_m
            if diff > 0:
                gain += diff
        return gain

    def total_elevation_loss_m(self) -> float:
        loss = 0.0
        for i in range(1, len(self.points)):
            diff = self.points[i].elevation_m - self.points[i-1].elevation_m
            if diff < 0:
                loss += abs(diff)
        return loss

    def total_distance_km(self) -> float:
        if not self.points:
            return 0.0
        return self.points[-1].distance_km

    def max_elevation_m(self) -> float:
        if not self.points:
            return 0.0
        return max(p.elevation_m for p in self.points)

    def min_elevation_m(self) -> float:
        if not self.points:
            return 0.0
        return min(p.elevation_m for p in self.points)

    def avg_slope_pct(self) -> float:
        if self.total_distance_km() == 0:
            return 0.0
        return (self.total_elevation_gain_m() / (self.total_distance_km() * 1000)) * 100

    def max_slope_pct(self) -> float:
        max_slope = 0.0
        for i in range(1, len(self.points)):
            dist = self.points[i].distance_km - self.points[i-1].distance_km
            if dist > 0:
                elev_diff = self.points[i].elevation_m - self.points[i-1].elevation_m
                slope = (elev_diff / (dist * 1000)) * 100
                max_slope = max(max_slope, abs(slope))
        return max_slope

    def stats(self) -> Dict:
        return {
            "route": self.route_name,
            "distance_km": round(self.total_distance_km(), 2),
            "elevation_gain_m": round(self.total_elevation_gain_m(), 1),
            "elevation_loss_m": round(self.total_elevation_loss_m(), 1),
            "max_elevation_m": round(self.max_elevation_m(), 1),
            "min_elevation_m": round(self.min_elevation_m(), 1),
            "avg_slope_pct": round(self.avg_slope_pct(), 1),
            "max_slope_pct": round(self.max_slope_pct(), 1),
        }

def run():
    epc = ElevationProfileCalculator(
        route_name="Mountain Trail",
        points=[
            ElevationPoint(0, 500),
            ElevationPoint(2, 800),
            ElevationPoint(4, 1200),
            ElevationPoint(6, 1000),
            ElevationPoint(8, 1500),
            ElevationPoint(10, 500),
        ]
    )
    print(epc.stats())

if __name__ == "__main__":
    run()
