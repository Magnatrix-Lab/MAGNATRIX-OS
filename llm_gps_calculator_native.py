"""GPS Calculator — coordinate math, distance, bearing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class GPS:
    lat: float
    lon: float

    @staticmethod
    def to_radians(d: float) -> float:
        return d * math.pi / 180

    def distance_to(self, other: 'GPS') -> float:
        R = 6371000
        dlat = self.to_radians(other.lat - self.lat)
        dlon = self.to_radians(other.lon - self.lon)
        a = math.sin(dlat/2)**2 + math.cos(self.to_radians(self.lat)) * math.cos(self.to_radians(other.lat)) * math.sin(dlon/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

    def bearing_to(self, other: 'GPS') -> float:
        dlon = self.to_radians(other.lon - self.lon)
        y = math.sin(dlon) * math.cos(self.to_radians(other.lat))
        x = math.cos(self.to_radians(self.lat)) * math.sin(self.to_radians(other.lat)) - math.sin(self.to_radians(self.lat)) * math.cos(self.to_radians(other.lat)) * math.cos(dlon)
        brng = math.atan2(y, x)
        return (math.degrees(brng) + 360) % 360

    def midpoint(self, other: 'GPS') -> 'GPS':
        dlon = self.to_radians(other.lon - self.lon)
        Bx = math.cos(self.to_radians(other.lat)) * math.cos(dlon)
        By = math.cos(self.to_radians(other.lat)) * math.sin(dlon)
        lat3 = math.atan2(math.sin(self.to_radians(self.lat)) + math.sin(self.to_radians(other.lat)), math.sqrt((math.cos(self.to_radians(self.lat)) + Bx)**2 + By**2))
        lon3 = self.to_radians(self.lon) + math.atan2(By, math.cos(self.to_radians(self.lat)) + Bx)
        return GPS(round(math.degrees(lat3), 6), round(math.degrees(lon3), 6))

    def stats(self) -> Dict:
        return {"lat": self.lat, "lon": self.lon}

def run():
    a = GPS(40.7128, -74.0060)
    b = GPS(51.5074, -0.1278)
    print(f"Distance: {a.distance_to(b)/1000:.2f} km")
    print(f"Bearing: {a.bearing_to(b):.1f}")
    print(a.midpoint(b).stats())

if __name__ == "__main__":
    run()
