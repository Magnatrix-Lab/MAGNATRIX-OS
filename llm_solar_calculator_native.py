"""Solar Calculator — irradiance, panel output, angle optimization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class SolarCalculator:
    latitude: float = 0.0
    panel_tilt: float = 30.0
    panel_azimuth: float = 180.0
    efficiency: float = 0.20
    area: float = 10.0

    def declination(self, day_of_year: int) -> float:
        return 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))

    def hour_angle(self, hour: float) -> float:
        return 15 * (hour - 12)

    def solar_elevation(self, day: int, hour: float) -> float:
        dec = math.radians(self.declination(day))
        lat = math.radians(self.latitude)
        ha = math.radians(self.hour_angle(hour))
        sin_alt = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(ha)
        return math.degrees(math.asin(max(-1, min(1, sin_alt))))

    def incident_angle(self, day: int, hour: float) -> float:
        elev = math.radians(self.solar_elevation(day, hour))
        tilt = math.radians(self.panel_tilt)
        return math.degrees(math.acos(max(-1, min(1, math.cos(elev) * math.cos(tilt)))))

    def power_output(self, irradiance: float, day: int, hour: float) -> float:
        angle = math.radians(self.incident_angle(day, hour))
        return irradiance * self.area * self.efficiency * math.cos(angle) if angle < math.pi/2 else 0

    def optimal_tilt(self, day: int) -> float:
        return abs(self.declination(day) - self.latitude)

    def stats(self, day: int, hour: float) -> Dict:
        return {"elevation": self.solar_elevation(day, hour), "optimal_tilt": self.optimal_tilt(day)}

def run():
    sc = SolarCalculator(latitude=40.7, panel_tilt=30)
    print("Elevation:", sc.solar_elevation(172, 12))
    print("Power:", sc.power_output(1000, 172, 12))
    print(sc.stats(172, 12))

if __name__ == "__main__":
    run()
