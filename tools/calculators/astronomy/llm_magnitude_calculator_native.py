"""Native stdlib module: Magnitude Calculator
Calculates apparent magnitude, absolute magnitude, and distance modulus.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class MagnitudeCalculator:
    apparent_magnitude: float
    distance_parsec: float
    absolute_magnitude: float = 0.0

    def distance_modulus(self) -> float:
        return 5 * math.log10(self.distance_parsec) - 5

    def calculate_absolute_magnitude(self) -> float:
        return self.apparent_magnitude - self.distance_modulus()

    def calculate_apparent_magnitude(self) -> float:
        return self.absolute_magnitude + self.distance_modulus()

    def distance_from_modulus(self) -> float:
        return 10 ** ((self.apparent_magnitude - self.absolute_magnitude + 5) / 5)

    def luminosity_ratio(self, other_absolute_mag: float) -> float:
        return 10 ** (0.4 * (other_absolute_mag - self.absolute_magnitude))

    def stats(self) -> Dict:
        return {
            "apparent_magnitude": self.apparent_magnitude,
            "distance_parsec": self.distance_parsec,
            "distance_modulus": round(self.distance_modulus(), 2),
            "absolute_magnitude": round(self.calculate_absolute_magnitude(), 2),
            "distance_from_modulus_pc": round(self.distance_from_modulus(), 2),
        }

def run():
    mc = MagnitudeCalculator(apparent_magnitude=4.83, distance_parsec=10)
    print(mc.stats())

if __name__ == "__main__":
    run()
