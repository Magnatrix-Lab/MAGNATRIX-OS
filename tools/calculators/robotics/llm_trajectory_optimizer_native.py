"""Trajectory Optimizer — Lambert, porkchop, delta-v minimization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from math import sqrt, pi, radians, degrees, sin, cos, atan2, acos, fabs, pow, fmod, isnan
from datetime import datetime, timedelta

class TransferType(Enum):
    DIRECT = auto()
    GRAVITY_ASSIST = auto()
    AEROBRAKING = auto()

@dataclass
class Body:
    name: str
    mu: float  # km^3/s^2
    radius: float  # km
    orbital_radius: float  # km from sun (or central body)
    orbital_period: float  # days

class LambertSolver:
    """Simplified Lambert problem solver for direct transfers."""
    @staticmethod
    def solve(r1: Tuple[float, float, float], r2: Tuple[float, float, float],
              tof: float, mu: float, prograde: bool = True) -> Tuple[float, float]:
        """Return (v1, v2) delta-v magnitudes for transfer."""
        r1_mag = sqrt(r1[0]**2 + r1[1]**2 + r1[2]**2)
        r2_mag = sqrt(r2[0]**2 + r2[1]**2 + r2[2]**2)
        a_transfer = (r1_mag + r2_mag) / 2
        if a_transfer <= 0 or mu <= 0:
            return (0.0, 0.0)
        v_transfer1 = sqrt(mu * (2 / r1_mag - 1 / a_transfer))
        v_transfer2 = sqrt(mu * (2 / r2_mag - 1 / a_transfer))
        v1_orbital = sqrt(mu / r1_mag)
        v2_orbital = sqrt(mu / r2_mag)
        dv1 = fabs(v_transfer1 - v1_orbital)
        dv2 = fabs(v_transfer2 - v2_orbital)
        return (dv1, dv2)

@dataclass
class PorkchopPlot:
    origin: Body
    destination: Body
    mu_central: float = 1.32712440018e11  # Sun km^3/s^2

    def sweep(self, start_date: datetime, dep_range_days: int = 300,
              tof_range_days: int = 500, step_days: int = 10) -> List[Dict]:
        """Generate porkchop plot data points."""
        results = []
        r1 = self.origin.orbital_radius
        r2 = self.destination.orbital_radius
        for dep in range(0, dep_range_days, step_days):
            for tof in range(50, tof_range_days, step_days):
                tof_sec = tof * 86400
                dv1, dv2 = LambertSolver.solve(
                    (r1, 0.0, 0.0), (r2, 0.0, 0.0), tof_sec, self.mu_central
                )
                total_dv = dv1 + dv2
                if not isnan(total_dv) and total_dv > 0:
                    results.append({
                        "departure_days": dep,
                        "tof_days": tof,
                        "dv_departure": dv1,
                        "dv_arrival": dv2,
                        "total_dv": total_dv,
                        "c3": dv1 ** 2
                    })
        return results

    def find_optimal(self, start_date: datetime, dep_range_days: int = 300,
                     tof_range_days: int = 500, step_days: int = 10) -> Optional[Dict]:
        """Find minimum delta-v trajectory."""
        points = self.sweep(start_date, dep_range_days, tof_range_days, step_days)
        if not points:
            return None
        best = min(points, key=lambda x: x["total_dv"])
        return best

@dataclass
class TrajectoryOptimizer:
    transfers: List[Dict] = field(default_factory=list)

    def add_transfer(self, origin: Body, destination: Body, tof: float, date: datetime) -> None:
        r1 = origin.orbital_radius
        r2 = destination.orbital_radius
        dv1, dv2 = LambertSolver.solve((r1, 0, 0), (r2, 0, 0), tof, 1.32712440018e11)
        self.transfers.append({
            "origin": origin.name,
            "destination": destination.name,
            "date": date,
            "tof_sec": tof,
            "dv_total": dv1 + dv2,
            "c3": dv1 ** 2
        })

    def best_transfer(self) -> Optional[Dict]:
        if not self.transfers:
            return None
        return min(self.transfers, key=lambda x: x["dv_total"])

    def stats(self) -> Dict[str, float]:
        if not self.transfers:
            return {}
        dvs = [t["dv_total"] for t in self.transfers]
        return {
            "transfer_count": len(self.transfers),
            "min_dv_kms": min(dvs),
            "max_dv_kms": max(dvs),
            "avg_dv_kms": sum(dvs) / len(dvs)
        }

# Planetary constants
EARTH = Body("Earth", 398600.4418, 6378.137, 149.6e6, 365.25)
MARS = Body("Mars", 42828.0, 3396.2, 227.9e6, 687.0)
VENUS = Body("Venus", 324859.0, 6051.8, 108.2e6, 224.7)

def run():
    porkchop = PorkchopPlot(EARTH, MARS)
    start = datetime(2024, 1, 1)
    optimal = porkchop.find_optimal(start, dep_range_days=200, tof_range_days=400, step_days=20)
    print(f"Optimal Earth→Mars: {optimal}")
    points = porkchop.sweep(start, dep_range_days=100, tof_range_days=200, step_days=30)
    print(f"Swept {len(points)} points")
    opt = TrajectoryOptimizer()
    opt.add_transfer(EARTH, MARS, 200 * 86400, start)
    opt.add_transfer(EARTH, VENUS, 150 * 86400, start)
    print(opt.stats())
    print(opt.best_transfer())

if __name__ == "__main__":
    run()
