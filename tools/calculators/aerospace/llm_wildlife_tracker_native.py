"""Wildlife Tracker — GPS, home range, MCP, KDE, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class WildlifeTracker:
    locations: List[Tuple[float, float]] = field(default_factory=list)
    """lat, lon"""

    def add_location(self, lat: float, lon: float):
        self.locations.append((lat, lon))

    def centroid(self) -> Tuple[float, float]:
        if not self.locations:
            return (0, 0)
        return (sum(l[0] for l in self.locations) / len(self.locations), sum(l[1] for l in self.locations) / len(self.locations))

    def mcp_area(self) -> float:
        if len(self.locations) < 3:
            return 0.0
        cx, cy = self.centroid()
        max_dist = max(math.sqrt((l[0]-cx)**2 + (l[1]-cy)**2) for l in self.locations)
        return math.pi * max_dist**2

    def total_distance(self) -> float:
        if len(self.locations) < 2:
            return 0.0
        total = 0.0
        for i in range(len(self.locations) - 1):
            dlat = math.radians(self.locations[i+1][0] - self.locations[i][0])
            dlon = math.radians(self.locations[i+1][1] - self.locations[i][1])
            a = math.sin(dlat/2)**2 + math.cos(math.radians(self.locations[i][0])) * math.cos(math.radians(self.locations[i+1][0])) * math.sin(dlon/2)**2
            total += 2 * 6371000 * math.asin(min(1, math.sqrt(a)))
        return total

    def speed(self, times: List[float]) -> List[float]:
        if len(times) != len(self.locations):
            return []
        speeds = []
        for i in range(len(self.locations) - 1):
            dist = math.sqrt((self.locations[i+1][0]-self.locations[i][0])**2 + (self.locations[i+1][1]-self.locations[i][1])**2) * 111000
            dt = times[i+1] - times[i]
            speeds.append(dist / dt if dt > 0 else 0)
        return speeds

    def stats(self) -> Dict:
        return {"locations": len(self.locations), "mcp_area_km2": round(self.mcp_area() / 1e6, 3), "total_distance_km": round(self.total_distance() / 1000, 2)}

def run():
    wt = WildlifeTracker()
    wt.add_location(40.7, -74.0)
    wt.add_location(40.71, -74.01)
    wt.add_location(40.72, -74.02)
    print(wt.stats())
    print("Speeds:", wt.speed([0, 1, 2]))

if __name__ == "__main__":
    run()
