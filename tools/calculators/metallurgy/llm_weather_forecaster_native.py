"""Weather Forecaster — persistence, trend, moving average, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class WeatherForecaster:
    temps: List[float] = field(default_factory=list)
    pressures: List[float] = field(default_factory=list)
    humidities: List[float] = field(default_factory=list)

    def persistence_forecast(self, days: int = 1) -> float:
        return self.temps[-1] if self.temps else 0.0

    def moving_avg_forecast(self, window: int = 3) -> float:
        if len(self.temps) < window:
            return sum(self.temps) / len(self.temps) if self.temps else 0.0
        return sum(self.temps[-window:]) / window

    def trend_forecast(self, days: int = 1) -> float:
        n = len(self.temps)
        if n < 2:
            return self.temps[-1] if self.temps else 0.0
        x = list(range(n))
        mx, my = sum(x)/n, sum(self.temps)/n
        b = sum((xi-mx)*(yi-my) for xi,yi in zip(x,self.temps)) / sum((xi-mx)**2 for xi in x)
        a = my - b * mx
        return a + b * (n - 1 + days)

    def pressure_trend(self) -> str:
        if len(self.pressures) < 2:
            return "steady"
        diff = self.pressures[-1] - self.pressures[-2]
        if diff > 1:
            return "rising"
        elif diff < -1:
            return "falling"
        return "steady"

    def stats(self) -> Dict:
        return {"persistence": self.persistence_forecast(), "ma": self.moving_avg_forecast(), "trend": round(self.trend_forecast(), 1)}

def run():
    wf = WeatherForecaster(temps=[22,23,24,23,25], pressures=[1013,1012,1010,1008])
    print(wf.stats())
    print("Pressure trend:", wf.pressure_trend())

if __name__ == "__main__":
    run()
