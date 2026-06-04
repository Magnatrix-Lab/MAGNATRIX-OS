#!/usr/bin/env python3
"""MAGNATRIX-OS :: Temperature Forecaster Native Module
Predicts temperature using seasonal decomposition, trend analysis, and thermal inertia modeling.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional


class Season(Enum):
    WINTER = auto()
    SPRING = auto()
    SUMMER = auto()
    AUTUMN = auto()

    @classmethod
    def from_month(cls, month: int) -> "Season":
        if month in (12, 1, 2):
            return cls.WINTER
        elif month in (3, 4, 5):
            return cls.SPRING
        elif month in (6, 7, 8):
            return cls.SUMMER
        return cls.AUTUMN


@dataclass
class DailyReading:
    day: int
    month: int
    year: int
    min_temp: float
    max_temp: float
    avg_temp: float
    humidity: float
    cloud_cover: float


@dataclass
class TemperatureForecast:
    predicted_min: float
    predicted_max: float
    predicted_avg: float
    confidence_interval: float
    season: Season
    trend_direction: str
    thermal_inertia: float
    days_ahead: int

    def to_dict(self) -> Dict:
        return {
            "predicted_min": round(self.predicted_min, 1),
            "predicted_max": round(self.predicted_max, 1),
            "predicted_avg": round(self.predicted_avg, 1),
            "confidence": round(self.confidence_interval, 2),
            "season": self.season.name,
            "trend": self.trend_direction,
            "days_ahead": self.days_ahead,
        }


class TemperatureForecaster:
    """Forecasts temperature using historical patterns and thermal inertia."""

    SEASONAL_BASE: Dict[Season, float] = {
        Season.WINTER: 15.0,
        Season.SPRING: 22.0,
        Season.SUMMER: 30.0,
        Season.AUTUMN: 20.0,
    }

    def __init__(self, location: str, latitude: float):
        self.location = location
        self.latitude = latitude
        self.history: List[DailyReading] = []
        self.thermal_inertia_coeff = 0.3

    def add_reading(self, reading: DailyReading) -> None:
        self.history.append(reading)

    def moving_average(self, days: int = 7) -> List[float]:
        if len(self.history) < days:
            return [r.avg_temp for r in self.history]
        result = []
        for i in range(len(self.history) - days + 1):
            window = self.history[i:i + days]
            result.append(sum(r.avg_temp for r in window) / days)
        return result

    def compute_trend(self, window: int = 14) -> float:
        if len(self.history) < window:
            return 0.0
        recent = self.history[-window:]
        x = list(range(len(recent)))
        y = [r.avg_temp for r in recent]
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return 0.0
        slope = (n * sum_xy - sum_x * sum_y) / denom
        return slope

    def thermal_inertia_factor(self, humidity: float, cloud_cover: float) -> float:
        return 1.0 - self.thermal_inertia_coeff * (humidity / 100.0) * cloud_cover

    def forecast(self, days_ahead: int = 1, current_humidity: float = 60.0, current_cloud: float = 0.5) -> TemperatureForecast:
        if not self.history:
            season = Season.SPRING
            base = self.SEASONAL_BASE[season]
            return TemperatureForecast(base - 5, base + 5, base, 5.0, season, "stable", 1.0, days_ahead)
        last = self.history[-1]
        season = Season.from_month(last.month)
        base = self.SEASONAL_BASE[season]
        lat_adjustment = -abs(self.latitude) * 0.1
        trend = self.compute_trend()
        ma = self.moving_average(7)
        recent_avg = ma[-1] if ma else last.avg_temp
        inertia = self.thermal_inertia_factor(current_humidity, current_cloud)
        predicted_avg = recent_avg + (trend * days_ahead * inertia) + lat_adjustment
        seasonal_var = 3.0 if season in (Season.SPRING, Season.AUTUMN) else 2.0
        confidence = seasonal_var * math.sqrt(days_ahead)
        trend_dir = "warming" if trend > 0.1 else "cooling" if trend < -0.1 else "stable"
        return TemperatureForecast(
            predicted_min=predicted_avg - confidence,
            predicted_max=predicted_avg + confidence,
            predicted_avg=predicted_avg,
            confidence_interval=confidence,
            season=season,
            trend_direction=trend_dir,
            thermal_inertia=inertia,
            days_ahead=days_ahead,
        )

    def stats(self) -> Dict[str, float]:
        if not self.history:
            return {"readings": 0, "avg": 0.0, "range": 0.0}
        temps = [r.avg_temp for r in self.history]
        return {
            "readings": len(self.history),
            "avg": round(sum(temps) / len(temps), 2),
            "range": round(max(temps) - min(temps), 2),
        }


def run() -> None:
    forecaster = TemperatureForecaster("Jakarta", -6.2)
    for i in range(30):
        forecaster.add_reading(DailyReading(
            day=i + 1, month=6, year=2024,
            min_temp=22.0 + i * 0.1,
            max_temp=32.0 + i * 0.15,
            avg_temp=27.0 + i * 0.12,
            humidity=75.0,
            cloud_cover=0.4,
        ))
    forecast = forecaster.forecast(days_ahead=3, current_humidity=78.0, current_cloud=0.5)
    print(f"Temperature Forecaster Demo:")
    print(f"  Forecast: {forecast.predicted_min:.1f} - {forecast.predicted_max:.1f} C (avg: {forecast.predicted_avg:.1f} C)")
    print(f"  Trend: {forecast.trend_direction}, Season: {forecast.season.name}")
    print(f"  Stats: {forecaster.stats()}")


if __name__ == "__main__":
    run()
