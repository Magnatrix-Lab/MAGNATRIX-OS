"""Map Projection - Simple map projections for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

class ProjectionType(Enum):
    MERCATOR = auto(); EQUIRECTANGULAR = auto()

@dataclass
class MapProjection:
    projection_type: ProjectionType = ProjectionType.MERCATOR
    
    def project(self, lat: float, lon: float) -> Tuple[float, float]:
        if self.projection_type == ProjectionType.MERCATOR:
            x = lon * math.pi / 180
            y = math.log(math.tan(math.pi/4 + math.radians(lat)/2))
            return x, y
        elif self.projection_type == ProjectionType.EQUIRECTANGULAR:
            return lon, lat
        return lon, lat
    
    def inverse(self, x: float, y: float) -> Tuple[float, float]:
        if self.projection_type == ProjectionType.MERCATOR:
            lon = math.degrees(x)
            lat = math.degrees(2 * math.atan(math.exp(y)) - math.pi/2)
            return lat, lon
        elif self.projection_type == ProjectionType.EQUIRECTANGULAR:
            return y, x
        return y, x
    
    def stats(self, lat: float, lon: float) -> dict:
        x, y = self.project(lat, lon)
        return {"projection": self.projection_type.name, "x": round(x, 4), "y": round(y, 4)}

def run():
    mp = MapProjection(ProjectionType.MERCATOR)
    lat, lon = 40.7128, -74.0060  # NYC
    x, y = mp.project(lat, lon)
    print(f"Projected: ({x:.4f}, {y:.4f})")
    lat2, lon2 = mp.inverse(x, y)
    print(f"Inverse: ({lat2:.4f}, {lon2:.4f})")
    print("Stats:", mp.stats(lat, lon))

if __name__ == "__main__": run()
