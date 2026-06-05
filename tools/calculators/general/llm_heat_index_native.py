"""Native stdlib module: Heat Index Calculator
Calculates heat index, wind chill, and apparent temperature.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class HeatIndexCalculator:
    temperature_c: float
    humidity_pct: float
    wind_speed_kmh: float = 0.0

    def heat_index_c(self) -> float:
        t = self.temperature_c
        rh = self.humidity_pct
        if t < 27 or rh < 40:
            return t
        hi = -8.784694755 + 1.61139411*t + 2.338548839*rh - 0.14611605*t*rh
        hi += -0.012308094*t**2 - 0.016424828*rh**2 + 0.002211732*t**2*rh
        hi += 0.00072546*t*rh**2 - 0.000003582*t**2*rh**2
        return hi

    def wind_chill_c(self) -> float:
        t = self.temperature_c
        v = self.wind_speed_kmh
        if t > 10 or v < 4.8:
            return t
        return 13.12 + 0.6215*t - 11.37*(v**0.16) + 0.3965*t*(v**0.16)

    def apparent_temperature(self) -> float:
        if self.temperature_c >= 27:
            return self.heat_index_c()
        elif self.temperature_c <= 10 and self.wind_speed_kmh >= 4.8:
            return self.wind_chill_c()
        return self.temperature_c

    def comfort_level(self) -> str:
        at = self.apparent_temperature()
        if at < 0:
            return "extreme_cold"
        elif at < 10:
            return "cold"
        elif at < 18:
            return "cool"
        elif at < 24:
            return "comfortable"
        elif at < 29:
            return "warm"
        elif at < 35:
            return "hot"
        return "extreme_heat"

    def stats(self) -> Dict:
        return {
            "temperature_c": self.temperature_c,
            "humidity_pct": self.humidity_pct,
            "wind_speed_kmh": self.wind_speed_kmh,
            "heat_index_c": round(self.heat_index_c(), 1),
            "wind_chill_c": round(self.wind_chill_c(), 1),
            "apparent_temp_c": round(self.apparent_temperature(), 1),
            "comfort": self.comfort_level(),
        }

def run():
    hi = HeatIndexCalculator(temperature_c=35, humidity_pct=65, wind_speed_kmh=10)
    print(hi.stats())

if __name__ == "__main__":
    run()
