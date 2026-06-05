"""Navigation Calculator — heading, course, drift, fix, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class NavigationCalculator:
    def true_heading(self, course: float, wind_direction: float, wind_speed: float, airspeed: float) -> float:
        """Simplified wind triangle."""
        wd = math.radians(wind_direction - course)
        ws = wind_speed / airspeed if airspeed > 0 else 0
        correction = math.degrees(math.asin(ws * math.sin(wd))) if abs(ws * math.sin(wd)) <= 1 else 0
        return course + correction

    def ground_speed(self, course: float, wind_direction: float, wind_speed: float, airspeed: float) -> float:
        wd = math.radians(wind_direction - course)
        return airspeed * math.cos(math.asin(min(1, wind_speed / airspeed * math.sin(wd)))) + wind_speed * math.cos(wd) if airspeed > 0 else 0.0

    def distance_to(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return 2 * 3440 * math.asin(min(1, math.sqrt(a)))

    def bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        dlon = math.radians(lon2 - lon1)
        y = math.sin(dlon) * math.cos(math.radians(lat2))
        x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    def time_enroute(self, distance: float, ground_speed: float) -> float:
        return distance / ground_speed if ground_speed > 0 else 0.0

    def stats(self, lat1: float, lon1: float, lat2: float, lon2: float) -> Dict:
        d = self.distance_to(lat1, lon1, lat2, lon2)
        b = self.bearing(lat1, lon1, lat2, lon2)
        return {"distance_nm": round(d, 1), "bearing": round(b, 1)}

def run():
    nav = NavigationCalculator()
    print(nav.stats(40.7, -74.0, 51.5, -0.1))
    print("Ground speed:", nav.ground_speed(90, 270, 20, 120))

if __name__ == "__main__":
    run()
