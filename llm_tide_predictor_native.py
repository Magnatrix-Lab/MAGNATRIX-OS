"""Tide Predictor — harmonic constituents, tidal height, slack water, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from math import sin, cos, pi, radians, sqrt, fmod, fabs
from datetime import datetime, timedelta

class TideType(Enum):
    SEMI_DIURNAL = auto()
    DIURNAL = auto()
    MIXED = auto()

@dataclass
class HarmonicConstituent:
    name: str
    speed: float  # degrees per hour
    amplitude: float  # meters
    phase: float  # degrees at equilibrium argument

@dataclass
class TideStation:
    name: str
    latitude: float
    longitude: float
    constituents: List[HarmonicConstituent] = field(default_factory=list)
    mean_level: float = 0.0

    def height_at(self, t: datetime) -> float:
        """Calculate tidal height at time t using harmonic constituents."""
        hours = t.hour + t.minute / 60.0 + t.second / 3600.0
        days = t.timetuple().tm_yday
        total = self.mean_level
        for c in self.constituents:
            angle = radians(c.speed * hours + c.phase + days * 0.5)
            total += c.amplitude * sin(angle)
        return total

    def find_extremes(self, start: datetime, hours: float = 24.0) -> List[Dict]:
        """Find high/low tides in a given period."""
        extremes = []
        step = timedelta(minutes=10)
        prev = self.height_at(start)
        prev_t = start
        current = start + step
        direction = 0  # 1 = rising, -1 = falling
        while current < start + timedelta(hours=hours):
            h = self.height_at(current)
            if h > prev and direction <= 0:
                if direction == -1:
                    extremes.append({"time": prev_t, "height": prev, "type": "low"})
                direction = 1
            elif h < prev and direction >= 0:
                if direction == 1:
                    extremes.append({"time": prev_t, "height": prev, "type": "high"})
                direction = -1
            prev = h
            prev_t = current
            current += step
        return extremes

    def slack_water_times(self, start: datetime, hours: float = 24.0) -> List[datetime]:
        """Approximate slack water times (near high/low tide)."""
        extremes = self.find_extremes(start, hours)
        return [e["time"] for e in extremes]

    def stats(self) -> Dict[str, float]:
        amplitudes = [c.amplitude for c in self.constituents]
        return {
            "mean_level_m": self.mean_level,
            "max_amplitude_m": max(amplitudes) if amplitudes else 0.0,
            "constituent_count": len(self.constituents),
            "spring_range_m": sum(amplitudes) * 2 if amplitudes else 0.0
        }

class TidePredictor:
    def __init__(self, stations: List[TideStation] = None):
        self.stations = stations or []

    def add_station(self, station: TideStation) -> None:
        self.stations.append(station)

    def predict(self, station_name: str, t: datetime) -> Optional[float]:
        for s in self.stations:
            if s.name == station_name:
                return s.height_at(t)
        return None

    def stats(self) -> Dict[str, int]:
        return {
            "station_count": len(self.stations),
            "total_constituents": sum(len(s.constituents) for s in self.stations)
        }

def run():
    station = TideStation(
        name="Jakarta",
        latitude=-6.2,
        longitude=106.8,
        mean_level=1.2,
        constituents=[
            HarmonicConstituent("M2", 28.984, 0.8, 0.0),
            HarmonicConstituent("S2", 30.0, 0.3, 30.0),
            HarmonicConstituent("K1", 15.041, 0.4, 90.0),
            HarmonicConstituent("O1", 13.943, 0.2, 120.0),
        ]
    )
    t = datetime(2024, 6, 1, 12, 0, 0)
    print(f"Height at {t}: {station.height_at(t):.2f} m")
    extremes = station.find_extremes(t, hours=48)
    print(f"Found {len(extremes)} tides in 48h")
    for e in extremes[:4]:
        print(f"  {e['type'].upper()} tide at {e['time'].strftime('%m-%d %H:%M')}: {e['height']:.2f} m")
    print(station.stats())

if __name__ == "__main__":
    run()
