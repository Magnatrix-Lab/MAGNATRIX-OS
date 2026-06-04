"""Demand Forecaster — moving average, seasonal, exponential smoothing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class ForecastMethod(Enum):
    MA = auto()
    EWMA = auto()
    SEASONAL = auto()

class DemandForecaster:
    def __init__(self, method: ForecastMethod = ForecastMethod.EWMA):
        self.method = method
        self.history: List[float] = []
        self.forecasts: List[float] = []
        self.alpha = 0.3
        self.season_length = 12

    def add_history(self, values: List[float]):
        self.history.extend(values)

    def forecast(self, periods: int = 1) -> List[float]:
        if self.method == ForecastMethod.MA:
            return self._ma_forecast(periods)
        elif self.method == ForecastMethod.EWMA:
            return self._ewma_forecast(periods)
        elif self.method == ForecastMethod.SEASONAL:
            return self._seasonal_forecast(periods)
        return []

    def _ma_forecast(self, periods: int, window: int = 3) -> List[float]:
        result = []
        for _ in range(periods):
            if len(self.history) >= window:
                val = sum(self.history[-window:]) / window
            else:
                val = sum(self.history) / len(self.history) if self.history else 0
            result.append(val)
            self.history.append(val)
        return result

    def _ewma_forecast(self, periods: int) -> List[float]:
        result = []
        if not self.history:
            return result
        s = self.history[0]
        for v in self.history[1:]:
            s = self.alpha * v + (1 - self.alpha) * s
        for _ in range(periods):
            result.append(s)
            s = self.alpha * s + (1 - self.alpha) * s
        return result

    def _seasonal_forecast(self, periods: int) -> List[float]:
        if len(self.history) < self.season_length * 2:
            return self._ma_forecast(periods)
        seasonal = []
        for i in range(self.season_length):
            vals = [self.history[j] for j in range(i, len(self.history), self.season_length)]
            seasonal.append(sum(vals) / len(vals) if vals else 0)
        trend = (self.history[-1] - self.history[-self.season_length]) / self.season_length
        result = []
        for i in range(periods):
            idx = i % self.season_length
            val = seasonal[idx] + trend * (i + 1)
            result.append(val)
        return result

    def mape(self, actual: List[float], predicted: List[float]) -> float:
        errors = [abs((a - p) / a) for a, p in zip(actual, predicted) if a != 0]
        return sum(errors) / len(errors) * 100 if errors else 0

    def stats(self) -> Dict:
        return {"history": len(self.history), "method": self.method.name, "season": self.season_length}

def run():
    fc = DemandForecaster(ForecastMethod.EWMA)
    fc.add_history([100, 105, 110, 108, 115, 120, 118, 125])
    print("Forecast:", fc.forecast(3))
    print(fc.stats())

if __name__ == "__main__":
    run()
