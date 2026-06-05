"""Launch Window — planet alignment, synodic period, parking orbit, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from math import sqrt, pi, radians, degrees, sin, cos, acos, atan2, ceil
from datetime import datetime, timedelta

class OrbitType(Enum):
    CIRCULAR = auto()
    ELLIPTICAL = auto()
    PARKING = auto()

@dataclass
class Planet:
    name: str
    mu: float  # gravitational parameter km^3/s^2
    radius: float  # km
    orbital_period: float  # days
    mean_distance: float  # AU or km

@dataclass
class ParkingOrbit:
    altitude: float  # km above surface
    inclination: float  # degrees
    raan: float = 0.0  # right ascension of ascending node
    type: OrbitType = OrbitType.PARKING

@dataclass
class LaunchWindow:
    departure: datetime
    arrival: datetime
    phase_angle: float  # degrees
    departure_dv: float  # km/s
    arrival_dv: float  # km/s
    total_dv: float  # km/s
    tof_days: float  # time of flight in days
    c3: float  # km^2/s^2 (characteristic energy)

class PlanetaryConstants:
    EARTH = Planet("Earth", 398600.4418, 6378.137, 365.25, 149.6e6)
    MARS = Planet("Mars", 42828.0, 3396.2, 687.0, 227.9e6)
    VENUS = Planet("Venus", 324859.0, 6051.8, 224.7, 108.2e6)
    JUPITER = Planet("Jupiter", 126686534.0, 71492.0, 4332.8, 778.5e6)
    MOON = Planet("Moon", 4902.8, 1737.4, 27.3, 384400.0)

@dataclass
class LaunchWindowPlanner:
    origin: Planet
    destination: Planet
    parking_orbit: ParkingOrbit
    windows: List[LaunchWindow] = field(default_factory=list)

    def synodic_period(self) -> float:
        """Return synodic period in days."""
        p1 = self.origin.orbital_period
        p2 = self.destination.orbital_period
        return abs(p1 * p2 / (p1 - p2)) if p1 != p2 else float('inf')

    def hohmann_transfer_time(self) -> float:
        """Time of flight for Hohmann transfer in days."""
        a_transfer = (self.origin.mean_distance + self.destination.mean_distance) / 2
        period_transfer = 2 * pi * sqrt(a_transfer**3 / self.origin.mu) / 86400
        return period_transfer / 2

    def phase_angle(self) -> float:
        """Phase angle at departure for Hohmann transfer in degrees."""
        tof = self.hohmann_transfer_time() * 86400  # seconds
        p2 = self.destination.orbital_period * 86400
        return 180.0 - degrees(2 * pi * tof / p2)

    def departure_velocity(self) -> float:
        """Velocity relative to departure planet for transfer."""
        r1 = self.origin.mean_distance
        r2 = self.destination.mean_distance
        a = (r1 + r2) / 2
        v_departure = sqrt(self.origin.mu * (2 / r1 - 1 / a))
        v_orbit = sqrt(self.origin.mu / r1)
        return abs(v_departure - v_orbit)

    def arrival_velocity(self) -> float:
        """Velocity relative to destination planet at arrival."""
        r1 = self.origin.mean_distance
        r2 = self.destination.mean_distance
        a = (r1 + r2) / 2
        v_arrival = sqrt(self.destination.mu * (2 / r2 - 1 / a))
        v_orbit = sqrt(self.destination.mu / r2)
        return abs(v_arrival - v_orbit)

    def c3_energy(self) -> float:
        """Characteristic energy (C3) for departure."""
        v_inf = self.departure_velocity()
        return v_inf ** 2

    def parking_orbit_velocity(self) -> float:
        """Velocity in circular parking orbit."""
        r = self.origin.radius + self.parking_orbit.altitude
        return sqrt(self.origin.mu / r)

    def delta_v_departure(self) -> float:
        """Total delta-v needed for departure burn."""
        v_park = self.parking_orbit_velocity()
        v_inf = self.departure_velocity()
        return abs(v_inf - v_park) if v_inf > v_park else 0.0

    def delta_v_arrival(self) -> float:
        """Total delta-v needed for arrival/capture."""
        r_dest = self.destination.radius + 500.0  # assume 500km capture orbit
        v_capture = sqrt(self.destination.mu / r_dest)
        v_inf = self.arrival_velocity()
        return abs(v_inf - v_capture) if v_inf > v_capture else 0.0

    def find_windows(self, start_date: datetime, count: int = 5) -> List[LaunchWindow]:
        """Find next launch windows using synodic period."""
        synodic = self.synodic_period()
        phase = self.phase_angle()
        windows = []
        for i in range(count):
            departure = start_date + timedelta(days=synodic * i)
            tof = self.hohmann_transfer_time()
            arrival = departure + timedelta(days=tof)
            dv_dep = self.delta_v_departure()
            dv_arr = self.delta_v_arrival()
            lw = LaunchWindow(
                departure=departure,
                arrival=arrival,
                phase_angle=phase,
                departure_dv=dv_dep,
                arrival_dv=dv_arr,
                total_dv=dv_dep + dv_arr,
                tof_days=tof,
                c3=self.c3_energy()
            )
            windows.append(lw)
        self.windows = windows
        return windows

    def stats(self) -> Dict[str, float]:
        return {
            "synodic_period_days": self.synodic_period(),
            "hohmann_tof_days": self.hohmann_transfer_time(),
            "phase_angle_deg": self.phase_angle(),
            "departure_dv_kms": self.delta_v_departure(),
            "arrival_dv_kms": self.delta_v_arrival(),
            "c3_km2s2": self.c3_energy(),
            "parking_orbit_velocity_kms": self.parking_orbit_velocity()
        }

def run():
    earth = PlanetaryConstants.EARTH
    mars = PlanetaryConstants.MARS
    parking = ParkingOrbit(altitude=200.0, inclination=28.5)
    planner = LaunchWindowPlanner(earth, mars, parking)
    start = datetime(2024, 1, 1)
    windows = planner.find_windows(start, count=3)
    print(f"Synodic period: {planner.synodic_period():.1f} days")
    for i, w in enumerate(windows, 1):
        print(f"Window {i}: dep={w.departure.date()}, arr={w.arrival.date()}, "
              f"phase={w.phase_angle:.1f}°, C3={w.c3:.2f}, total_dv={w.total_dv:.3f} km/s")
    print(planner.stats())

if __name__ == "__main__":
    run()
