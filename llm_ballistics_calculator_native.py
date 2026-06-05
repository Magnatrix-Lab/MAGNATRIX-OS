"""Native stdlib module: Ballistics Calculator
Calculates projectile trajectories, muzzle velocities, and ranges.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class BallisticsCalculator:
    muzzle_velocity_m_s: float
    angle_deg: float
    projectile_mass_g: float
    drag_coefficient: float = 0.3

    def range_m(self) -> float:
        g = 9.81
        angle = math.radians(self.angle_deg)
        v = self.muzzle_velocity_m_s
        return (v ** 2 * math.sin(2 * angle)) / g

    def max_height_m(self) -> float:
        g = 9.81
        angle = math.radians(self.angle_deg)
        v = self.muzzle_velocity_m_s
        return (v ** 2 * (math.sin(angle) ** 2)) / (2 * g)

    def time_of_flight_s(self) -> float:
        g = 9.81
        angle = math.radians(self.angle_deg)
        v = self.muzzle_velocity_m_s
        return (2 * v * math.sin(angle)) / g

    def kinetic_energy_j(self) -> float:
        m = self.projectile_mass_g / 1000
        return 0.5 * m * (self.muzzle_velocity_m_s ** 2)

    def momentum_kg_m_s(self) -> float:
        m = self.projectile_mass_g / 1000
        return m * self.muzzle_velocity_m_s

    def effective_range_m(self, min_energy_j: float = 100) -> float:
        if self.kinetic_energy_j() == 0:
            return 0.0
        return self.range_m() * (self.kinetic_energy_j() / (self.kinetic_energy_j() + min_energy_j))

    def stats(self) -> Dict:
        return {
            "muzzle_velocity_m_s": self.muzzle_velocity_m_s,
            "angle_deg": self.angle_deg,
            "range_m": round(self.range_m(), 1),
            "max_height_m": round(self.max_height_m(), 1),
            "time_of_flight_s": round(self.time_of_flight_s(), 2),
            "kinetic_energy_j": round(self.kinetic_energy_j(), 1),
            "momentum_kg_m_s": round(self.momentum_kg_m_s(), 3),
        }

def run():
    bc = BallisticsCalculator(muzzle_velocity_m_s=850, angle_deg=45, projectile_mass_g=10)
    print(bc.stats())

if __name__ == "__main__":
    run()
