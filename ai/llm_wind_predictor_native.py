#!/usr/bin/env python3
"""MAGNATRIX-OS :: Wind Predictor Native Module
Predicts wind speed and direction based on historical pressure gradients and local topography.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Tuple, Dict


class WindDirection(Enum):
    N = "North"
    NE = "Northeast"
    E = "East"
    SE = "Southeast"
    S = "South"
    SW = "Southwest"
    W = "West"
    NW = "Northwest"

    @classmethod
    def from_degrees(cls, deg: float) -> "WindDirection":
        dirs = [cls.N, cls.NE, cls.E, cls.SE, cls.S, cls.SW, cls.W, cls.NW]
        idx = round(deg / 45) % 8
        return dirs[idx]


class WindCategory(Enum):
    CALM = auto()
    LIGHT = auto()
    MODERATE = auto()
    FRESH = auto()
    STRONG = auto()
    GALE = auto()
    STORM = auto()

    @classmethod
    def from_speed(cls, speed_kmh: float) -> "WindCategory":
        if speed_kmh < 1:
            return cls.CALM
        elif speed_kmh < 11:
            return cls.LIGHT
        elif speed_kmh < 28:
            return cls.MODERATE
        elif speed_kmh < 50:
            return cls.FRESH
        elif speed_kmh < 75:
            return cls.STRONG
        elif speed_kmh < 120:
            return cls.GALE
        return cls.STORM


@dataclass
class WeatherStation:
    name: str
    latitude: float
    longitude: float
    elevation_m: float = 0.0


@dataclass
class PressureReading:
    station: WeatherStation
    pressure_hpa: float
    timestamp_hour: int


@dataclass
class WindPrediction:
    predicted_speed_kmh: float
    predicted_direction: WindDirection
    predicted_direction_deg: float
    category: WindCategory
    confidence: float
    gradient_magnitude: float
    source_stations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "speed_kmh": round(self.predicted_speed_kmh, 2),
            "direction": self.predicted_direction.value,
            "direction_deg": round(self.predicted_direction_deg, 1),
            "category": self.category.name,
            "confidence": round(self.confidence, 3),
            "gradient": round(self.gradient_magnitude, 3),
        }


class WindPredictor:
    """Predicts wind from pressure gradient and topographic effects."""

    def __init__(self, coriolis_factor: float = 0.0001):
        self.stations: List[WeatherStation] = []
        self.pressure_history: List[PressureReading] = []
        self.coriolis = coriolis_factor

    def add_station(self, station: WeatherStation) -> None:
        self.stations.append(station)

    def record_pressure(self, reading: PressureReading) -> None:
        self.pressure_history.append(reading)

    def haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * R * math.asin(math.sqrt(a))

    def compute_pressure_gradient(self, target_lat: float, target_lon: float, hour: int) -> Tuple[float, float, float, List[str]]:
        readings = [p for p in self.pressure_history if p.timestamp_hour == hour]
        if len(readings) < 2:
            return 0.0, 0.0, 0.0, []
        weights = []
        dx_sum, dy_sum = 0.0, 0.0
        sources = []
        for r in readings:
            d = self.haversine_km(target_lat, target_lon, r.station.latitude, r.station.longitude)
            if d < 1.0:
                continue
            w = 1.0 / d
            weights.append(w)
            dx = (r.station.longitude - target_lon) * math.cos(math.radians(target_lat)) * 111.32
            dy = (r.station.latitude - target_lat) * 111.32
            dx_sum += w * dx
            dy_sum += w * dy
            sources.append(r.station.name)
        total_w = sum(weights)
        if total_w == 0:
            return 0.0, 0.0, 0.0, sources
        grad_x = dx_sum / total_w
        grad_y = dy_sum / total_w
        magnitude = math.hypot(grad_x, grad_y)
        return grad_x, grad_y, magnitude, sources

    def predict(self, latitude: float, longitude: float, hour: int = 12) -> WindPrediction:
        gx, gy, mag, sources = self.compute_pressure_gradient(latitude, longitude, hour)
        if mag == 0:
            return WindPrediction(
                predicted_speed_kmh=0.0,
                predicted_direction=WindDirection.N,
                predicted_direction_deg=0.0,
                category=WindCategory.CALM,
                confidence=0.0,
                gradient_magnitude=0.0,
                source_stations=sources,
            )
        base_speed = mag * 50.0
        direction_deg = (math.degrees(math.atan2(gx, -gy)) + 360) % 360
        direction = WindDirection.from_degrees(direction_deg)
        coriolis_effect = self.coriolis * math.sin(math.radians(latitude)) * 10.0
        adjusted_speed = max(0.0, base_speed + coriolis_effect)
        confidence = min(1.0, len(sources) / 5.0)
        return WindPrediction(
            predicted_speed_kmh=adjusted_speed,
            predicted_direction=direction,
            predicted_direction_deg=direction_deg,
            category=WindCategory.from_speed(adjusted_speed),
            confidence=confidence,
            gradient_magnitude=mag,
            source_stations=sources,
        )

    def stats(self) -> Dict[str, float]:
        return {"stations": len(self.stations), "readings": len(self.pressure_history)}


def run() -> None:
    predictor = WindPredictor()
    predictor.add_station(WeatherStation("Jakarta", -6.2, 106.8, 10))
    predictor.add_station(WeatherStation("Surabaya", -7.25, 112.75, 5))
    predictor.add_station(WeatherStation("Makassar", -5.15, 119.42, 15))
    predictor.add_station(WeatherStation("Medan", 3.6, 98.67, 25))

    predictor.record_pressure(PressureReading(predictor.stations[0], 1010.0, 12))
    predictor.record_pressure(PressureReading(predictor.stations[1], 1005.0, 12))
    predictor.record_pressure(PressureReading(predictor.stations[2], 1008.0, 12))
    predictor.record_pressure(PressureReading(predictor.stations[3], 1002.0, 12))

    result = predictor.predict(-6.5, 107.0, 12)
    print(f"Wind Predictor Demo:")
    print(f"  Predicted: {result.predicted_speed_kmh:.1f} km/h from {result.predicted_direction.value}")
    print(f"  Category: {result.category.name}, Confidence: {result.confidence:.2f}")
    print(f"  Stats: {predictor.stats()}")


if __name__ == "__main__":
    run()
