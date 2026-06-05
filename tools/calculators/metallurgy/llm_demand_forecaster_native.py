"""Native stdlib module: Demand Forecaster
Simple moving average and exponential smoothing demand forecasting.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class DemandForecaster:
    product_name: str
    historical_demand: List[float] = field(default_factory=list)
    smoothing_alpha: float = 0.3

    def moving_average(self, periods: int = 3) -> float:
        if len(self.historical_demand) < periods:
            return sum(self.historical_demand) / max(1, len(self.historical_demand))
        return sum(self.historical_demand[-periods:]) / periods

    def exponential_smoothing(self) -> float:
        if not self.historical_demand:
            return 0.0
        forecast = self.historical_demand[0]
        for actual in self.historical_demand[1:]:
            forecast = self.smoothing_alpha * actual + (1 - self.smoothing_alpha) * forecast
        return forecast

    def trend(self) -> float:
        if len(self.historical_demand) < 2:
            return 0.0
        return self.historical_demand[-1] - self.historical_demand[0]

    def forecast_next(self) -> float:
        return self.exponential_smoothing() + (self.trend() / max(1, len(self.historical_demand) - 1))

    def stats(self) -> Dict[str, float]:
        return {
            "product": self.product_name,
            "ma_3": round(self.moving_average(3), 1),
            "exp_smoothing": round(self.exponential_smoothing(), 1),
            "trend": round(self.trend(), 1),
            "forecast_next": round(self.forecast_next(), 1),
        }

def run():
    df = DemandForecaster(
        product_name="Widget-X",
        historical_demand=[120, 135, 128, 142, 150, 145, 160],
        smoothing_alpha=0.4
    )
    print(df.stats())

if __name__ == "__main__":
    run()
