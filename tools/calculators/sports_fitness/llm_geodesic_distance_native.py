"""Native stdlib module: Geodesic Distance Calculator
Calculates great-circle and rhumb-line distances between coordinates.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class GeodesicDistanceCalculator:
    lat1: float
    lon1: float
    lat2: float
    lon2: float

    def haversine_km(self) -> float:
        R = 6371.0
        phi1, phi2 = math.radians(self.lat1), math.radians(self.lat2)
        dphi = math.radians(self.lat2 - self.lat1)
        dlambda = math.radians(self.lon2 - self.lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def haversine_nm(self) -> float:
        return self.haversine_km() / 1.852

    def initial_bearing(self) -> float:
        phi1, phi2 = math.radians(self.lat1), math.radians(self.lat2)
        dlambda = math.radians(self.lon2 - self.lon1)
        x = math.sin(dlambda) * math.cos(phi2)
        y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360

    def midpoint(self) -> tuple:
        phi1, phi2 = math.radians(self.lat1), math.radians(self.lat2)
        dlambda = math.radians(self.lon2 - self.lon1)
        Bx = math.cos(phi2) * math.cos(dlambda)
        By = math.cos(phi2) * math.sin(dlambda)
        lat3 = math.degrees(math.atan2(math.sin(phi1) + math.sin(phi2), math.sqrt((math.cos(phi1) + Bx)**2 + By**2)))
        lon3 = self.lon1 + math.degrees(math.atan2(By, math.cos(phi1) + Bx))
        return (round(lat3, 6), round(lon3, 6))

    def stats(self) -> Dict:
        return {
            "distance_km": round(self.haversine_km(), 3),
            "distance_nm": round(self.haversine_nm(), 3),
            "initial_bearing": round(self.initial_bearing(), 1),
            "midpoint": self.midpoint(),
        }

def run():
    gdc = GeodesicDistanceCalculator(lat1=51.5074, lon1=-0.1278, lat2=48.8566, lon2=2.3522)
    print(gdc.stats())

if __name__ == "__main__":
    run()
