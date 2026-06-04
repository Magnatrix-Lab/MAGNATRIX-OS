"""Satellite Tracker — TLE-style, pass prediction, azimuth/elevation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from math import sqrt, pi, radians, degrees, sin, cos, atan2, acos, fmod, fabs
from datetime import datetime, timedelta

class PassType(Enum):
    VISIBLE = auto()
    DAYLIGHT = auto()
    NIGHT = auto()

@dataclass
class GroundStation:
    lat: float  # degrees
    lon: float  # degrees
    altitude: float = 0.0  # meters
    name: str = "Station"

@dataclass
class SatelliteState:
    """Simplified SGP4-like state."""
    inclination: float  # degrees
    raan: float  # degrees
    eccentricity: float
    arg_perigee: float  # degrees
    mean_anomaly: float  # degrees
    mean_motion: float  # revs/day
    epoch: datetime

    @property
    def period_sec(self) -> float:
        return 86400.0 / self.mean_motion

    def mean_anomaly_at(self, t: datetime) -> float:
        dt = (t - self.epoch).total_seconds()
        n = 2 * pi / self.period_sec
        M = radians(self.mean_anomaly) + n * dt
        return fmod(degrees(M), 360.0)

    def semi_major_axis(self, mu: float = 398600.4418) -> float:
        n = 2 * pi / self.period_sec
        return (mu / (n ** 2)) ** (1.0 / 3.0)

    def position_eci(self, t: datetime) -> Tuple[float, float, float]:
        """Return ECI position (x, y, z) in km."""
        a = self.semi_major_axis()
        e = self.eccentricity
        M = radians(self.mean_anomaly_at(t))
        E = M
        for _ in range(10):
            delta = (E - e * sin(E) - M) / (1 - e * cos(E))
            E -= delta
            if fabs(delta) < 1e-10:
                break
        r = a * (1 - e * cos(E))
        v = 2 * atan2(sqrt(1 + e) * sin(E / 2), sqrt(1 - e) * cos(E / 2))
        u = v + radians(self.arg_perigee)
        x = r * (cos(radians(self.raan)) * cos(u) - sin(radians(self.raan)) * sin(u) * cos(radians(self.inclination)))
        y = r * (sin(radians(self.raan)) * cos(u) + cos(radians(self.raan)) * sin(u) * cos(radians(self.inclination)))
        z = r * sin(u) * sin(radians(self.inclination))
        return (x, y, z)

@dataclass
class SatellitePass:
    start: datetime
    end: datetime
    max_elevation: float
    aos_azimuth: float  # acquisition of signal
    los_azimuth: float  # loss of signal
    pass_type: PassType

class SatelliteTracker:
    def __init__(self, satellite: SatelliteState, ground: GroundStation):
        self.sat = satellite
        self.ground = ground

    def _geodetic_to_eci(self, t: datetime) -> Tuple[float, float, float]:
        """Simplified ECI position of ground station (km)."""
        lat = radians(self.ground.lat)
        lon = radians(self.ground.lon)
        re = 6378.137
        theta = lon + 2 * pi * (t.hour + t.minute / 60 + t.second / 3600) / 24
        x = re * cos(lat) * cos(theta)
        y = re * cos(lat) * sin(theta)
        z = re * sin(lat)
        return (x, y, z)

    def _azimuth_elevation(self, sat_pos: Tuple[float, float, float], ground_eci: Tuple[float, float, float]) -> Tuple[float, float]:
        dx = sat_pos[0] - ground_eci[0]
        dy = sat_pos[1] - ground_eci[1]
        dz = sat_pos[2] - ground_eci[2]
        r = sqrt(dx * dx + dy * dy + dz * dz)
        elevation = degrees(asin(dz / r)) if r > 0 else 0
        azimuth = degrees(atan2(dy, dx)) % 360
        return (azimuth, elevation)

    def predict_passes(self, start: datetime, hours: float = 24, min_elevation: float = 10.0) -> List[SatellitePass]:
        passes = []
        current = start
        step = timedelta(minutes=1)
        end = start + timedelta(hours=hours)
        in_pass = False
        pass_start = None
        max_el = 0.0
        aos_az = 0.0
        while current < end:
            sat_pos = self.sat.position_eci(current)
            ground_eci = self._geodetic_to_eci(current)
            az, el = self._azimuth_elevation(sat_pos, ground_eci)
            if el > min_elevation and not in_pass:
                in_pass = True
                pass_start = current
                aos_az = az
                max_el = el
            elif in_pass:
                if el > max_el:
                    max_el = el
                if el < min_elevation:
                    in_pass = False
                    p = SatellitePass(
                        start=pass_start,
                        end=current,
                        max_elevation=max_el,
                        aos_azimuth=aos_az,
                        los_azimuth=az,
                        pass_type=PassType.NIGHT
                    )
                    passes.append(p)
            current += step
        return passes

    def stats(self) -> Dict[str, float]:
        return {
            "orbital_period_min": self.sat.period_sec / 60,
            "semi_major_axis_km": self.sat.semi_major_axis(),
            "eccentricity": self.sat.eccentricity,
            "inclination_deg": self.sat.inclination
        }

def run():
    sat = SatelliteState(
        inclination=51.6, raan=0.0, eccentricity=0.0007,
        arg_perigee=0.0, mean_anomaly=0.0, mean_motion=15.5,
        epoch=datetime(2024, 1, 1, 12, 0, 0)
    )
    gs = GroundStation(lat=-6.2, lon=106.8, name="Jakarta")
    tracker = SatelliteTracker(sat, gs)
    start = datetime(2024, 1, 1, 12, 0, 0)
    passes = tracker.predict_passes(start, hours=48)
    print(f"Predicted {len(passes)} passes in 48h")
    for p in passes[:3]:
        print(f"  {p.start.strftime('%H:%M')}-{p.end.strftime('%H:%M')}, max_el={p.max_elevation:.1f}°")
    print(tracker.stats())

if __name__ == "__main__":
    run()
