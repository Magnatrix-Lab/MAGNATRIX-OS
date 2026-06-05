"""Native stdlib module: Salinity Calculator
Calculates seawater density, salinity, and freezing point depression.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class SalinityCalculator:
    salinity_ppt: float
    temperature_c: float
    pressure_dbar: float = 0.0

    def density_kg_m3(self) -> float:
        t = self.temperature_c
        s = self.salinity_ppt
        return 1028 - 0.125 * t + 0.78 * (s - 35)

    def freezing_point_c(self) -> float:
        return -0.0575 * self.salinity_ppt + 0.0017 * (self.salinity_ppt ** 1.5) - 0.0002 * self.salinity_ppt * self.temperature_c

    def sigma_t(self) -> float:
        return self.density_kg_m3() - 1000

    def conductivity_approx(self) -> float:
        return 4.291 * self.salinity_ppt / (1 + 0.0162 * (self.temperature_c - 25))

    def sound_speed_m_s(self) -> float:
        t = self.temperature_c
        s = self.salinity_ppt
        return 1449.2 + 4.6*t - 0.055*t**2 + 0.00029*t**3 + (1.34 - 0.01*t)*(s - 35)

    def stats(self) -> Dict:
        return {
            "salinity_ppt": self.salinity_ppt,
            "temperature_c": self.temperature_c,
            "density_kg_m3": round(self.density_kg_m3(), 2),
            "freezing_point_c": round(self.freezing_point_c(), 2),
            "sigma_t": round(self.sigma_t(), 2),
            "sound_speed_m_s": round(self.sound_speed_m_s(), 1),
        }

def run():
    sc = SalinityCalculator(salinity_ppt=35, temperature_c=15, pressure_dbar=100)
    print(sc.stats())

if __name__ == "__main__":
    run()
