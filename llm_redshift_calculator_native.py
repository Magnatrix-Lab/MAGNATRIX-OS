"""Native stdlib module: Redshift Calculator
Calculates redshift, recession velocity, and cosmological distances.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class RedshiftCalculator:
    observed_wavelength_nm: float
    emitted_wavelength_nm: float
    hubble_constant_km_s_mpc: float = 70.0

    def redshift(self) -> float:
        if self.emitted_wavelength_nm == 0:
            return 0.0
        return (self.observed_wavelength_nm - self.emitted_wavelength_nm) / self.emitted_wavelength_nm

    def recession_velocity_c(self) -> float:
        z = self.redshift()
        if z < 0.1:
            return z
        return ((z + 1)**2 - 1) / ((z + 1)**2 + 1)

    def recession_velocity_km_s(self) -> float:
        return self.recession_velocity_c() * 299792.458

    def distance_mpc(self) -> float:
        if self.hubble_constant_km_s_mpc == 0:
            return 0.0
        return self.recession_velocity_km_s() / self.hubble_constant_km_s_mpc

    def distance_mly(self) -> float:
        return self.distance_mpc() * 3.26156

    def age_of_universe_at_emission_gyr(self) -> float:
        z = self.redshift()
        if z < 0.01:
            return 13.8
        return 13.8 / (1 + z)**1.5

    def stats(self) -> Dict:
        return {
            "observed_wavelength_nm": self.observed_wavelength_nm,
            "emitted_wavelength_nm": self.emitted_wavelength_nm,
            "redshift": round(self.redshift(), 4),
            "recession_velocity_c": round(self.recession_velocity_c(), 4),
            "recession_velocity_km_s": round(self.recession_velocity_km_s(), 1),
            "distance_mpc": round(self.distance_mpc(), 1),
            "distance_mly": round(self.distance_mly(), 1),
        }

def run():
    rc = RedshiftCalculator(observed_wavelength_nm=656.5, emitted_wavelength_nm=486.1, hubble_constant_km_s_mpc=70)
    print(rc.stats())

if __name__ == "__main__":
    run()
