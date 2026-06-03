"""LLM Weather Analyzer — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class WeatherCondition(Enum):
    SUNNY = auto()
    CLOUDY = auto()
    RAINY = auto()
    STORMY = auto()
    SNOWY = auto()
    FOGGY = auto()

@dataclass
class WeatherReading:
    timestamp: str
    temperature: float
    humidity: float
    pressure: float
    wind_speed: float
    wind_direction: float
    condition: WeatherCondition
    metadata: Dict[str, Any] = field(default_factory=dict)

class WeatherAnalyzer:
    def __init__(self) -> None:
        self._readings: List[WeatherReading] = []

    def add_reading(self, reading: WeatherReading) -> None:
        self._readings.append(reading)

    def get_avg_temperature(self, last_n: int = 24) -> float:
        recent = self._readings[-last_n:]
        if not recent:
            return 0.0
        return sum(r.temperature for r in recent) / len(recent)

    def get_high_low(self, last_n: int = 24) -> tuple:
        recent = self._readings[-last_n:]
        if not recent:
            return (0.0, 0.0)
        return (max(r.temperature for r in recent), min(r.temperature for r in recent))

    def get_dominant_condition(self, last_n: int = 24) -> WeatherCondition:
        recent = self._readings[-last_n:]
        if not recent:
            return WeatherCondition.SUNNY
        counts = {}
        for r in recent:
            counts[r.condition] = counts.get(r.condition, 0) + 1
        return max(counts.items(), key=lambda x: x[1])[0]

    def heat_index(self, temperature: float, humidity: float) -> float:
        if temperature < 27 or humidity < 40:
            return temperature
        c = [-42.379, 2.04901523, 10.14333127, -0.22475541, -6.83783e-3, -5.481717e-2, 1.22874e-3, 8.5282e-4, -1.99e-6]
        T = temperature
        R = humidity
        HI = c[0] + c[1]*T + c[2]*R + c[3]*T*R + c[4]*T*T + c[5]*R*R + c[6]*T*T*R + c[7]*T*R*R + c[8]*T*T*R*R
        return HI

    def wind_chill(self, temperature: float, wind_speed: float) -> float:
        if temperature > 10 or wind_speed < 4.8:
            return temperature
        return 13.12 + 0.6215*temperature - 11.37*wind_speed**0.16 + 0.3965*temperature*wind_speed**0.16

    def get_forecast_trend(self) -> str:
        if len(self._readings) < 2:
            return "insufficient data"
        recent = self._readings[-10:]
        temps = [r.temperature for r in recent]
        if temps[-1] > temps[0] + 3:
            return "warming"
        elif temps[-1] < temps[0] - 3:
            return "cooling"
        return "stable"

    def get_stats(self) -> Dict[str, Any]:
        return {"readings": len(self._readings), "avg_temp": self.get_avg_temperature(), "high_low": self.get_high_low(), "dominant": self.get_dominant_condition().name}

def run() -> None:
    print("Weather Analyzer test")
    e = WeatherAnalyzer()
    for i in range(24):
        temp = 25 + 5 * math.sin(i * 0.3)
        e.add_reading(WeatherReading("h" + str(i), temp, 60 + i, 1013, 10, 180, WeatherCondition.SUNNY if i % 3 else WeatherCondition.CLOUDY))
    print("  Avg temp: " + str(e.get_avg_temperature()))
    print("  High/Low: " + str(e.get_high_low()))
    print("  Dominant: " + e.get_dominant_condition().name)
    print("  Heat index: " + str(e.heat_index(35, 70)))
    print("  Trend: " + e.get_forecast_trend())
    print("  Stats: " + str(e.get_stats()))
    print("Weather Analyzer test complete.")

if __name__ == "__main__":
    run()
