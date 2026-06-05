"""Macro Forecaster — GDP, inflation, unemployment, time series, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class MacroForecaster:
    gdp: List[float] = field(default_factory=list)
    inflation: List[float] = field(default_factory=list)
    unemployment: List[float] = field(default_factory=list)

    def growth_rate(self, series: List[float]) -> List[float]:
        return [(series[i] - series[i-1]) / series[i-1] * 100 for i in range(1, len(series))] if series else []

    def okun_law(self, gdp_change: float, beta: float = -0.5) -> float:
        return beta * gdp_change

    def phillips_curve(self, unemployment: float, natural: float = 5.0) -> float:
        return max(0, -0.5 * (unemployment - natural))

    def moving_average_forecast(self, series: List[float], window: int = 3) -> float:
        if len(series) < window:
            return sum(series) / len(series) if series else 0.0
        return sum(series[-window:]) / window

    def linear_forecast(self, series: List[float], periods: int = 1) -> float:
        n = len(series)
        if n < 2:
            return series[-1] if series else 0.0
        x = list(range(n))
        mx, my = sum(x)/n, sum(series)/n
        b = sum((xi - mx) * (yi - my) for xi, yi in zip(x, series)) / sum((xi - mx)**2 for xi in x)
        a = my - b * mx
        return a + b * (n - 1 + periods)

    def stats(self) -> Dict:
        return {"gdp_growth": self.growth_rate(self.gdp)[-1] if self.gdp else 0, "inflation": self.inflation[-1] if self.inflation else 0}

def run():
    mf = MacroForecaster(gdp=[100,105,110,115], inflation=[2,2.5,3,2.8], unemployment=[5,4.5,4,4.2])
    print("GDP growth:", mf.growth_rate(mf.gdp))
    print("Forecast:", mf.linear_forecast(mf.gdp))
    print(mf.stats())

if __name__ == "__main__":
    run()
