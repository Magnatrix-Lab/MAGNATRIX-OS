"""Native stdlib module: Barometer Calculator
Calculates pressure trends, altitude adjustments, and weather predictions.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class PressureReading:
    timestamp: str
    pressure_hpa: float
    temperature_c: float

@dataclass
class BarometerCalculator:
    location: str
    altitude_m: float
    readings: List[PressureReading] = field(default_factory=list)

    def sea_level_pressure(self, reading: PressureReading) -> float:
        return reading.pressure_hpa * (1 + (0.0065 * self.altitude_m) / (reading.temperature_c + 0.0065 * self.altitude_m + 273.15)) ** 5.257

    def current_sea_level_pressure(self) -> float:
        if not self.readings:
            return 0.0
        return self.sea_level_pressure(self.readings[-1])

    def pressure_trend_hpa_3h(self) -> float:
        if len(self.readings) < 2:
            return 0.0
        return self.readings[-1].pressure_hpa - self.readings[0].pressure_hpa

    def forecast(self) -> str:
        trend = self.pressure_trend_hpa_3h()
        if trend > 3:
            return "improving"
        elif trend > -1:
            return "steady"
        elif trend > -3:
            return "deteriorating"
        return "storm_approaching"

    def avg_pressure(self) -> float:
        if not self.readings:
            return 0.0
        return sum(r.pressure_hpa for r in self.readings) / len(self.readings)

    def stats(self) -> Dict:
        return {
            "location": self.location,
            "altitude_m": self.altitude_m,
            "readings": len(self.readings),
            "current_slp_hpa": round(self.current_sea_level_pressure(), 1),
            "trend_hpa": round(self.pressure_trend_hpa_3h(), 1),
            "forecast": self.forecast(),
            "avg_pressure_hpa": round(self.avg_pressure(), 1),
        }

def run():
    bc = BarometerCalculator(
        location="Mountain Station",
        altitude_m=1500,
        readings=[
            PressureReading("08:00", 850.5, 15),
            PressureReading("09:00", 851.2, 16),
            PressureReading("10:00", 852.0, 16),
            PressureReading("11:00", 852.8, 17),
        ]
    )
    print(bc.stats())

if __name__ == "__main__":
    run()
