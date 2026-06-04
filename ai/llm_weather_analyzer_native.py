"""Weather Analyzer - Weather data analysis for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math
from collections import defaultdict

class WeatherMetric(Enum):
    TEMPERATURE = auto(); HUMIDITY = auto(); PRESSURE = auto(); WIND = auto()

@dataclass
class WeatherAnalyzer:
    data: List[Dict] = field(default_factory=list)
    
    def add_reading(self, timestamp: str, metric: WeatherMetric, value: float, location: str = "") -> None:
        self.data.append({"timestamp": timestamp, "metric": metric.name, "value": value, "location": location})
    
    def average(self, metric: WeatherMetric, location: str = None) -> float:
        values = [d["value"] for d in self.data if d["metric"] == metric.name and (location is None or d["location"] == location)]
        return sum(values) / len(values) if values else 0.0
    
    def trend(self, metric: WeatherMetric) -> List[Tuple[str, float]]:
        readings = sorted([d for d in self.data if d["metric"] == metric.name], key=lambda x: x["timestamp"])
        return [(r["timestamp"], r["value"]) for r in readings]
    
    def stats(self, metric: WeatherMetric) -> dict:
        values = [d["value"] for d in self.data if d["metric"] == metric.name]
        if not values: return {}
        return {
            "metric": metric.name,
            "average": round(sum(values) / len(values), 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "readings": len(values)
        }

def run():
    wa = WeatherAnalyzer()
    wa.add_reading("2024-01-01", WeatherMetric.TEMPERATURE, 20.5, "NYC")
    wa.add_reading("2024-01-02", WeatherMetric.TEMPERATURE, 22.0, "NYC")
    wa.add_reading("2024-01-03", WeatherMetric.TEMPERATURE, 19.5, "NYC")
    wa.add_reading("2024-01-01", WeatherMetric.HUMIDITY, 60.0, "NYC")
    print("Temp avg:", wa.average(WeatherMetric.TEMPERATURE, "NYC"))
    print("Stats:", wa.stats(WeatherMetric.TEMPERATURE))

if __name__ == "__main__": run()
