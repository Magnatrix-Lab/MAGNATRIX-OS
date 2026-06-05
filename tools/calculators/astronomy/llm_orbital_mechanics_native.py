"""Native stdlib module: Orbital Mechanics Calculator
Calculates orbital parameters, velocities, and periods for celestial bodies.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class OrbitalMechanicsCalculator:
    semi_major_axis_m: float
    central_mass_kg: float
    eccentricity: float = 0.0

    G: float = 6.67430e-11

    def orbital_period_s(self) -> float:
        a = self.semi_major_axis_m
        return 2 * math.pi * math.sqrt(a**3 / (self.G * self.central_mass_kg))

    def orbital_period_days(self) -> float:
        return self.orbital_period_s() / 86400

    def orbital_velocity_m_s(self) -> float:
        a = self.semi_major_axis_m
        return math.sqrt(self.G * self.central_mass_kg / a)

    def periapsis_m(self) -> float:
        return self.semi_major_axis_m * (1 - self.eccentricity)

    def apoapsis_m(self) -> float:
        return self.semi_major_axis_m * (1 + self.eccentricity)

    def specific_orbital_energy_j_kg(self) -> float:
        a = self.semi_major_axis_m
        return -self.G * self.central_mass_kg / (2 * a)

    def escape_velocity_m_s(self) -> float:
        r = self.semi_major_axis_m
        return math.sqrt(2 * self.G * self.central_mass_kg / r)

    def stats(self) -> Dict:
        return {
            "semi_major_axis_m": f"{self.semi_major_axis_m:.2e}",
            "orbital_period_days": round(self.orbital_period_days(), 2),
            "orbital_velocity_m_s": round(self.orbital_velocity_m_s(), 2),
            "periapsis_m": f"{self.periapsis_m():.2e}",
            "apoapsis_m": f"{self.apoapsis_m():.2e}",
            "specific_energy_j_kg": round(self.specific_orbital_energy_j_kg(), 2),
            "escape_velocity_m_s": round(self.escape_velocity_m_s(), 2),
        }

def run():
    oc = OrbitalMechanicsCalculator(semi_major_axis_m=1.496e11, central_mass_kg=1.989e30, eccentricity=0.0167)
    print(oc.stats())

if __name__ == "__main__":
    run()
