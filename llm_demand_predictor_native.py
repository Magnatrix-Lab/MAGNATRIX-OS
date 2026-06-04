"""Demand Predictor — seasonality, trend, moving average, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class DemandPredictor:
    history: List[float] = field(default_factory=list)
    season_length: int = 12

    def moving_average(self, window: int = 3) -> float:
        if len(self.history) < window:
            return sum(self.history) / len(self.history) if self.history else 0.0
        return sum(self.history[-window:]) / window

    def seasonal_index(self) -> List[float]:
        if len(self.history) < self.season_length * 2:
            return [1.0] * self.season_length
        season_avg = [sum(self.history[i::self.season_length]) / len(self.history[i::self.season_length]) for i in range(self.season_length)]
        overall = sum(season_avg) / self.season_length
        return [s / overall if overall > 0 else 1.0 for s in season_avg]

    def forecast(self, periods: int = 1) -> List[float]:
        if not self.history:
            return [0.0] * periods
        trend = (self.history[-1] - self.history[0]) / len(self.history) if len(self.history) > 1 else 0
        base = self.moving_average()
        indices = self.seasonal_index()
        forecasts = []
        for i in range(periods):
            season_idx = (len(self.history) + i) % self.season_length
            forecasts.append((base + trend * (i + 1)) * indices[season_idx])
        return forecasts

    def stats(self) -> Dict:
        return {"mean": sum(self.history)/len(self.history) if self.history else 0, "forecast_next": self.forecast(1)[0] if self.history else 0}

def run():
    dp = DemandPredictor(history=[100,120,130,110,140,150,160,170])
    print(dp.stats())
    print("Forecast:", dp.forecast(3))

if __name__ == "__main__":
    run()
