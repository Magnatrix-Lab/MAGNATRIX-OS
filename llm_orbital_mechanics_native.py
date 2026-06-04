"""Orbital Mechanics — Kepler, two-body, Hohmann transfer, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from math import sqrt, pi, radians, degrees, sin, cos, acos, atan2, pow, fabs

class OrbitShape(Enum):
    CIRCULAR = auto()
    ELLIPTICAL = auto()
    PARABOLIC = auto()
    HYPERBOLIC = auto()

@dataclass
class OrbitalElements:
    a: float  # semi-major axis km
    e: float  # eccentricity
    i: float  # inclination degrees
    raan: float  # right ascension of ascending node degrees
    arg_pe: float  # argument of periapsis degrees
    true_anomaly: float  # degrees
    mu: float = 398600.4418  # km^3/s^2 (Earth default)

    @property
    def shape(self) -> OrbitShape:
        if self.e < 1e-6:
            return OrbitShape.CIRCULAR
        elif self.e < 1.0:
            return OrbitShape.ELLIPTICAL
        elif fabs(self.e - 1.0) < 1e-6:
            return OrbitShape.PARABOLIC
        else:
            return OrbitShape.HYPERBOLIC

    @property
    def period(self) -> float:
        """Orbital period in seconds."""
        if self.e >= 1.0:
            return float('inf')
        return 2 * pi * sqrt(self.a ** 3 / self.mu)

    @property
    def r_periapsis(self) -> float:
        return self.a * (1 - self.e)

    @property
    def r_apoapsis(self) -> float:
        return self.a * (1 + self.e)

    @property
    def velocity_circular(self) -> float:
        return sqrt(self.mu / self.a)

    @property
    def velocity_escape(self) -> float:
        return sqrt(2 * self.mu / self.a)

    def velocity_at(self, r: float) -> float:
        """Velocity at radius r using vis-viva equation."""
        return sqrt(self.mu * (2 / r - 1 / self.a))

    def kepler_equation(self, tol: float = 1e-10) -> float:
        """Solve Kepler equation for eccentric anomaly E."""
        M = radians(self.true_anomaly)  # mean anomaly approximation
        E = M
        for _ in range(50):
            delta = (E - self.e * sin(E) - M) / (1 - self.e * cos(E))
            E -= delta
            if abs(delta) < tol:
                break
        return E

    def position_velocity(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """Return (position, velocity) vectors in km and km/s."""
        r = self.a * (1 - self.e ** 2) / (1 + self.e * cos(radians(self.true_anomaly)))
        v = self.velocity_at(r)
        return ((r, 0.0, 0.0), (0.0, v, 0.0))

    def stats(self) -> Dict[str, float]:
        return {
            "period_sec": self.period,
            "r_periapsis_km": self.r_periapsis,
            "r_apoapsis_km": self.r_apoapsis,
            "v_circular_kms": self.velocity_circular,
            "v_escape_kms": self.velocity_escape,
            "eccentricity": self.e
        }

class HohmannTransfer:
    @staticmethod
    def delta_v(r1: float, r2: float, mu: float = 398600.4418) -> Tuple[float, float]:
        """Return (departure dv, arrival dv) in km/s."""
        a_transfer = (r1 + r2) / 2
        v1 = sqrt(mu / r1)
        v2 = sqrt(mu / r2)
        vt1 = sqrt(mu * (2 / r1 - 1 / a_transfer))
        vt2 = sqrt(mu * (2 / r2 - 1 / a_transfer))
        return (abs(vt1 - v1), abs(vt2 - v2))

    @staticmethod
    def transfer_time(r1: float, r2: float, mu: float = 398600.4418) -> float:
        """Transfer time in seconds."""
        a = (r1 + r2) / 2
        return pi * sqrt(a ** 3 / mu)

def run():
    orbit = OrbitalElements(a=7000.0, e=0.1, i=28.5, raan=0.0, arg_pe=0.0, true_anomaly=45.0)
    print(f"Shape: {orbit.shape.name}")
    print(f"Period: {orbit.period / 60:.1f} min")
    dv_dep, dv_arr = HohmannTransfer.delta_v(orbit.r_periapsis, 42164.0)
    tof = HohmannTransfer.transfer_time(orbit.r_periapsis, 42164.0)
    print(f"Hohmann to GEO: dv_dep={dv_dep:.3f} km/s, dv_arr={dv_arr:.3f} km/s, tof={tof/3600:.1f} h")
    print(orbit.stats())

if __name__ == "__main__":
    run()
