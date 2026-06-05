"""Native stdlib module: Dew Point Calculator
Calculates dew point, relative humidity, and saturation vapor pressure.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class DewPointCalculator:
    temperature_c: float
    relative_humidity_pct: float

    def saturation_vapor_pressure_hpa(self) -> float:
        t = self.temperature_c
        return 6.112 * math.exp((17.67 * t) / (t + 243.5))

    def actual_vapor_pressure_hpa(self) -> float:
        return self.saturation_vapor_pressure_hpa() * (self.relative_humidity_pct / 100)

    def dew_point_c(self) -> float:
        avp = self.actual_vapor_pressure_hpa()
        if avp <= 0:
            return self.temperature_c
        return (243.5 * math.log(avp / 6.112)) / (17.67 - math.log(avp / 6.112))

    def absolute_humidity_g_m3(self) -> float:
        avp = self.actual_vapor_pressure_hpa()
        t = self.temperature_c
        return (216.7 * avp) / (t + 273.15)

    def mixing_ratio_g_kg(self) -> float:
        avp = self.actual_vapor_pressure_hpa()
        p = 1013.25
        return 621.97 * (avp / (p - avp))

    def frost_point_c(self) -> float:
        if self.dew_point_c() > 0:
            return 0.0
        return self.dew_point_c()

    def stats(self) -> Dict:
        return {
            "temperature_c": self.temperature_c,
            "rh_pct": self.relative_humidity_pct,
            "dew_point_c": round(self.dew_point_c(), 1),
            "saturation_vp_hpa": round(self.saturation_vapor_pressure_hpa(), 2),
            "actual_vp_hpa": round(self.actual_vapor_pressure_hpa(), 2),
            "absolute_humidity_g_m3": round(self.absolute_humidity_g_m3(), 2),
            "mixing_ratio_g_kg": round(self.mixing_ratio_g_kg(), 2),
        }

def run():
    dp = DewPointCalculator(temperature_c=25, relative_humidity_pct=60)
    print(dp.stats())

if __name__ == "__main__":
    run()
