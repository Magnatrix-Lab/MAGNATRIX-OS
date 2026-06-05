"""Native stdlib module: VOR Navigation Calculator
Calculates VOR bearings, radials, and interception angles for instrument navigation.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class VORNavigationCalculator:
    vor_lat: float
    vor_lon: float
    aircraft_lat: float
    aircraft_lon: float
    desired_radial: float

    def _haversine_bearing(self) -> float:
        lat1, lon1 = math.radians(self.vor_lat), math.radians(self.vor_lon)
        lat2, lon2 = math.radians(self.aircraft_lat), math.radians(self.aircraft_lon)
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360

    def current_radial(self) -> float:
        return (self._haversine_bearing() + 180) % 360

    def distance_to_vor_nm(self) -> float:
        R = 3440.065
        lat1, lon1 = math.radians(self.vor_lat), math.radians(self.vor_lon)
        lat2, lon2 = math.radians(self.aircraft_lat), math.radians(self.aircraft_lon)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    def intercept_angle(self) -> float:
        radial_diff = self.desired_radial - self.current_radial()
        while radial_diff > 180:
            radial_diff -= 360
        while radial_diff < -180:
            radial_diff += 360
        return radial_diff

    def to_from(self) -> str:
        bearing = self._haversine_bearing()
        diff = abs(bearing - self.desired_radial)
        if diff > 180:
            diff = 360 - diff
        return "to" if diff < 90 else "from"

    def recommended_intercept_angle(self) -> float:
        ia = self.intercept_angle()
        if abs(ia) > 30:
            return 30 if ia > 0 else -30
        return ia

    def stats(self) -> Dict:
        return {
            "current_radial": round(self.current_radial(), 1),
            "distance_nm": round(self.distance_to_vor_nm(), 1),
            "intercept_angle": round(self.intercept_angle(), 1),
            "to_from": self.to_from(),
            "recommended_intercept": round(self.recommended_intercept_angle(), 1),
        }

def run():
    vor = VORNavigationCalculator(vor_lat=40.6397, vor_lon=-73.7789, aircraft_lat=40.5, aircraft_lon=-73.5, desired_radial=270)
    print(vor.stats())

if __name__ == "__main__":
    run()
