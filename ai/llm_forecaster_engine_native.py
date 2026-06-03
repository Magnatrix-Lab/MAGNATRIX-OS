"""Forecaster Engine - Time series forecasting for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto
import math

class ForecastMethod(Enum):
    MA = auto()
    EWMA = auto()
    LINEAR = auto()
    SEASONAL = auto()

@dataclass
class ForecasterEngine:
    method: ForecastMethod = ForecastMethod.EWMA
    alpha: float = 0.3
    seasonal_period: int = 7
    history: List[float] = field(default_factory=list)

    def fit(self, data: List[float]) -> None:
        self.history = data[:]

    def forecast(self, steps: int = 3) -> List[float]:
        if not self.history:
            return [0.0] * steps
        if self.method == ForecastMethod.MA:
            window = min(3, len(self.history))
            last = sum(self.history[-window:]) / window
            return [last] * steps
        if self.method == ForecastMethod.EWMA:
            s = self.history[0]
            for v in self.history[1:]:
                s = self.alpha * v + (1 - self.alpha) * s
            return [s] * steps
        if self.method == ForecastMethod.LINEAR:
            n = len(self.history)
            x = list(range(n))
            mean_x = sum(x) / n
            mean_y = sum(self.history) / n
            slope = sum((x[i]-mean_x)*(self.history[i]-mean_y) for i in range(n)) / sum((x[i]-mean_x)**2 for i in range(n)) if n > 1 else 0
            return [self.history[-1] + slope * (i+1) for i in range(steps)]
        if self.method == ForecastMethod.SEASONAL:
            period = self.seasonal_period
            pattern = []
            for i in range(period):
                vals = [self.history[j] for j in range(i, len(self.history), period)]
                pattern.append(sum(vals)/len(vals) if vals else 0)
            return [pattern[(len(self.history) + i) % period] for i in range(steps)]
        return [0.0] * steps

    def stats(self) -> dict:
        return {"method": self.method.name, "history_len": len(self.history), "forecast_steps": 3}

def run():
    for method in [ForecastMethod.MA, ForecastMethod.EWMA, ForecastMethod.LINEAR]:
        fc = ForecasterEngine(method, alpha=0.3)
        fc.fit([10, 12, 11, 13, 14, 12, 15])
        print(f"{method.name}: {fc.forecast(3)}")
    print("Stats:", fc.stats())

if __name__ == "__main__":
    run()
