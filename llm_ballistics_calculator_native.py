"""Ballistics Calculator — trajectory, drop, wind, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class BallisticsCalculator:
    muzzle_velocity: float = 800.0
    bullet_mass: float = 0.009
    bc: float = 0.3
    gravity: float = 9.81

    def drop(self, distance: float, time: float) -> float:
        return 0.5 * self.gravity * time**2

    def time_of_flight(self, distance: float) -> float:
        return distance / self.muzzle_velocity

    def trajectory(self, steps: int = 10, max_dist: float = 1000.0) -> List[Tuple[float, float]]:
        points = []
        for i in range(steps + 1):
            d = i * max_dist / steps
            t = self.time_of_flight(d)
            y = self.drop(d, t)
            points.append((d, -y))
        return points

    def wind_drift(self, distance: float, wind_speed: float, wind_angle: float) -> float:
        time = self.time_of_flight(distance)
        return wind_speed * math.sin(math.radians(wind_angle)) * time

    def energy(self, velocity: float) -> float:
        return 0.5 * self.bullet_mass * velocity**2

    def stats(self, distance: float = 500) -> Dict:
        t = self.time_of_flight(distance)
        return {"drop_m": round(self.drop(distance, t), 3), "tof_s": round(t, 3), "energy_j": round(self.energy(self.muzzle_velocity), 1)}

def run():
    bc = BallisticsCalculator()
    print(bc.stats(500))
    print("Trajectory:", bc.trajectory(5, 500))

if __name__ == "__main__":
    run()
