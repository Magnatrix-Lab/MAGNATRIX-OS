"""Native stdlib module: Bullet Trajectory Calculator
Calculates bullet trajectories, impact angles, and terminal ballistics.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class BulletTrajectoryCalculator:
    muzzle_velocity_m_s: float
    bullet_mass_g: float
    bullet_diameter_mm: float
    ballistic_coefficient: float
    sight_height_m: float = 0.0
    shooting_angle_deg: float = 0.0
    distance_m: float = 100.0

    def _drag_factor(self) -> float:
        return 0.5 * 1.225 * (math.pi * (self.bullet_diameter_mm / 2000) ** 2) / self.ballistic_coefficient

    def time_of_flight_s(self) -> float:
        v = self.muzzle_velocity_m_s
        if v <= 0:
            return 0.0
        return self.distance_m / v

    def drop_m(self) -> float:
        g = 9.81
        t = self.time_of_flight_s()
        angle = math.radians(self.shooting_angle_deg)
        return 0.5 * g * t ** 2 - self.sight_height_m - math.sin(angle) * self.distance_m

    def velocity_at_distance_m_s(self) -> float:
        v0 = self.muzzle_velocity_m_s
        drag = self._drag_factor()
        mass_kg = self.bullet_mass_g / 1000
        if mass_kg <= 0:
            return v0
        deceleration = drag * v0 ** 2 / mass_kg
        t = self.time_of_flight_s()
        return max(v0 - deceleration * t, 0)

    def kinetic_energy_j(self, velocity_m_s: float = None) -> float:
        v = velocity_m_s if velocity_m_s is not None else self.velocity_at_distance_m_s()
        mass_kg = self.bullet_mass_g / 1000
        return 0.5 * mass_kg * v ** 2

    def trajectory_angle_mrad(self) -> float:
        drop = self.drop_m()
        if self.distance_m == 0:
            return 0.0
        return math.atan(drop / self.distance_m) * 1000

    def impact_angle_deg(self) -> float:
        v0 = self.muzzle_velocity_m_s
        v = self.velocity_at_distance_m_s()
        if v0 <= 0:
            return 0.0
        return math.degrees(math.acos(max(min(v / v0, 1), -1)))

    def stats(self) -> Dict:
        v_dist = self.velocity_at_distance_m_s()
        return {
            "distance_m": self.distance_m,
            "time_of_flight_s": round(self.time_of_flight_s(), 3),
            "drop_m": round(self.drop_m(), 3),
            "velocity_at_distance_m_s": round(v_dist, 1),
            "kinetic_energy_j": round(self.kinetic_energy_j(v_dist), 1),
            "trajectory_angle_mrad": round(self.trajectory_angle_mrad(), 2),
            "impact_angle_deg": round(self.impact_angle_deg(), 2),
        }

def run():
    btc = BulletTrajectoryCalculator(
        muzzle_velocity_m_s=850,
        bullet_mass_g=9.5,
        bullet_diameter_mm=7.82,
        ballistic_coefficient=0.45,
        distance_m=300,
        shooting_angle_deg=0,
    )
    print(btc.stats())

if __name__ == "__main__":
    run()
