"""Native stdlib module: Magnetic Declination Calculator
Estimates magnetic declination, inclination, and field strength.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class MagneticDeclinationCalculator:
    latitude: float
    longitude: float
    altitude_m: float = 0
    year: int = 2024

    def _approximate_declination(self) -> float:
        return self.longitude * 0.5 + math.sin(math.radians(self.latitude)) * 10

    def _approximate_inclination(self) -> float:
        return math.degrees(math.atan(2 * math.tan(math.radians(self.latitude))))

    def _approximate_field_strength(self) -> float:
        base = 30000 + 20000 * math.cos(math.radians(self.latitude))
        return base * (1 - 0.00003 * self.altitude_m)

    def true_north_offset_deg(self) -> float:
        return self._approximate_declination()

    def magnetic_north_heading(self, true_heading: float) -> float:
        return (true_heading + self._approximate_declination()) % 360

    def true_north_heading(self, magnetic_heading: float) -> float:
        return (magnetic_heading - self._approximate_declination()) % 360

    def stats(self) -> Dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "declination_deg": round(self._approximate_declination(), 2),
            "inclination_deg": round(self._approximate_inclination(), 2),
            "field_strength_nt": round(self._approximate_field_strength(), 1),
            "altitude_m": self.altitude_m,
        }

def run():
    mdc = MagneticDeclinationCalculator(latitude=40.7, longitude=-74.0, altitude_m=10, year=2024)
    print(mdc.stats())

if __name__ == "__main__":
    run()
