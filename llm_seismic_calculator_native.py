"""Native stdlib module: Seismic Calculator
Calculates earthquake magnitude, intensity, and distance attenuation.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class SeismicCalculator:
    magnitude: float
    distance_km: float
    depth_km: float = 10.0

    def moment_magnitude(self) -> float:
        return self.magnitude

    def energy_joules(self) -> float:
        return 10 ** (1.5 * self.magnitude + 4.8)

    def energy_tons_tnt(self) -> float:
        return self.energy_joules() / 4.184e9

    def local_intensity_mmi(self) -> float:
        if self.distance_km <= 0:
            return self.magnitude * 1.5
        return self.magnitude + 6 - 1.66 * math.log10(self.distance_km) - 0.0008 * self.distance_km

    def peak_ground_acceleration_pctg(self) -> float:
        r = math.sqrt(self.distance_km**2 + self.depth_km**2)
        if r == 0:
            return 100.0
        return 10 ** (self.magnitude - 3.5 * math.log10(r) - 0.5)

    def felt_distance_km(self) -> float:
        return 10 ** (0.5 * self.magnitude - 1.5)

    def stats(self) -> Dict:
        return {
            "magnitude": self.magnitude,
            "distance_km": self.distance_km,
            "depth_km": self.depth_km,
            "energy_joules": f"{self.energy_joules():.2e}",
            "energy_tons_tnt": round(self.energy_tons_tnt(), 1),
            "local_intensity_mmi": round(self.local_intensity_mmi(), 1),
            "pga_pctg": round(self.peak_ground_acceleration_pctg(), 2),
            "felt_distance_km": round(self.felt_distance_km(), 1),
        }

def run():
    sc = SeismicCalculator(magnitude=6.5, distance_km=50, depth_km=15)
    print(sc.stats())

if __name__ == "__main__":
    run()
