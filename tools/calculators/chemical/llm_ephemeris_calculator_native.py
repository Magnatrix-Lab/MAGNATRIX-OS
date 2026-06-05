"""Ephemeris Calculator — sun/moon/planet positions, Julian date, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class EphemerisCalculator:
    def julian_date(self, year: int, month: int, day: int, hour: float = 0.0) -> float:
        if month <= 2:
            year -= 1
            month += 12
        A = int(year / 100)
        B = 2 - A + int(A / 4)
        return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5 + hour / 24

    def sun_position(self, jd: float) -> Tuple[float, float]:
        n = jd - 2451545.0
        L = 280.460 + 0.9856474 * n
        M = 357.528 + 0.9856003 * n
        M = math.radians(M % 360)
        eclon = L + 1.915 * math.sin(M) + 0.020 * math.sin(2*M)
        eclon = eclon % 360
        return eclon, 0.0

    def moon_position_approx(self, jd: float) -> Tuple[float, float]:
        n = jd - 2451545.0
        L = 218.316 + 13.176396 * n
        return L % 360, 5.13 * math.sin(math.radians(L))

    def sidereal_time(self, jd: float) -> float:
        n = jd - 2451545.0
        return 280.46061837 + 360.98564736629 * n

    def stats(self, year: int, month: int, day: int) -> Dict:
        jd = self.julian_date(year, month, day)
        return {"jd": jd, "sun": self.sun_position(jd), "moon": self.moon_position_approx(jd)}

def run():
    ec = EphemerisCalculator()
    print(ec.stats(2024, 6, 5))
    print("Sidereal:", ec.sidereal_time(ec.julian_date(2024, 6, 5, 12)))

if __name__ == "__main__":
    run()
