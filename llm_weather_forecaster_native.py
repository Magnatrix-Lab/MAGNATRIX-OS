"""Weather Forecaster — persistence, trend, pattern matching, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import statistics

class WeatherForecaster:
    def __init__(self, lookback: int = 7):
        self.lookback = lookback
        self.history: List[Dict] = []

    def add_reading(self, temp: float, humidity: float, pressure: float, wind: float, timestamp: float = 0):
        self.history.append({"temp": temp, "humidity": humidity, "pressure": pressure, "wind": wind, "time": timestamp})

    def forecast_temp(self, hours: int = 24) -> List[float]:
        if not self.history:
            return []
        recent = self.history[-self.lookback:]
        avg_change = 0
        if len(recent) > 1:
            changes = [recent[i]["temp"] - recent[i-1]["temp"] for i in range(1, len(recent))]
            avg_change = statistics.mean(changes)
        last = self.history[-1]["temp"]
        return [last + avg_change * h for h in range(1, hours + 1)]

    def forecast_pressure_trend(self) -> str:
        if len(self.history) < 3:
            return "STABLE"
        recent = self.history[-3:]
        if recent[-1]["pressure"] > recent[0]["pressure"] + 5:
            return "RISING"
        elif recent[-1]["pressure"] < recent[0]["pressure"] - 5:
            return "FALLING"
        return "STABLE"

    def rain_probability(self) -> float:
        if not self.history:
            return 0.0
        last = self.history[-1]
        prob = 0.0
        if last["humidity"] > 80:
            prob += 0.4
        if last["pressure"] < 1000:
            prob += 0.3
        if self.forecast_pressure_trend() == "FALLING":
            prob += 0.2
        return min(1.0, prob)

    def stats(self) -> Dict:
        return {"readings": len(self.history), "trend": self.forecast_pressure_trend()}

def run():
    wf = WeatherForecaster(5)
    wf.add_reading(20, 60, 1013, 10, 1)
    wf.add_reading(21, 65, 1010, 12, 2)
    wf.add_reading(22, 75, 1005, 15, 3)
    wf.add_reading(23, 85, 998, 18, 4)
    print("Temp forecast:", wf.forecast_temp(5))
    print("Rain prob:", wf.rain_probability())
    print(wf.stats())

if __name__ == "__main__":
    run()
