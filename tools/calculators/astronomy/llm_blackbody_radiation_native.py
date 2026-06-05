"""Native stdlib module: Blackbody Radiation Calculator
Calculates blackbody spectrum, peak wavelength, and luminosity.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class BlackbodyCalculator:
    temperature_k: float
    radius_m: float = 1.0

    K_B: float = 1.380649e-23
    H: float = 6.62607015e-34
    C: float = 2.99792458e8
    SIGMA: float = 5.670374419e-8

    def peak_wavelength_nm(self) -> float:
        b = 2.897771955e-3
        return (b / self.temperature_k) * 1e9

    def peak_frequency_hz(self) -> float:
        if self.peak_wavelength_nm() == 0:
            return 0.0
        return self.C / (self.peak_wavelength_nm() / 1e9)

    def spectral_radiance_peak_w_m3_sr(self) -> float:
        return (2 * self.H * self.C**2) / ((self.peak_wavelength_nm() / 1e9)**5) * (1 / (math.exp((self.H * self.C) / ((self.peak_wavelength_nm() / 1e9) * self.K_B * self.temperature_k)) - 1))

    def total_flux_w_m2(self) -> float:
        return self.SIGMA * self.temperature_k**4

    def luminosity_w(self) -> float:
        return 4 * math.pi * self.radius_m**2 * self.total_flux_w_m2()

    def solar_luminosity(self) -> float:
        if self.luminosity_w() == 0:
            return 0.0
        return self.luminosity_w() / 3.828e26

    def color_index_approx(self) -> str:
        t = self.temperature_k
        if t < 3000:
            return "red"
        elif t < 4500:
            return "orange"
        elif t < 6000:
            return "yellow"
        elif t < 10000:
            return "white"
        elif t < 30000:
            return "blue_white"
        return "blue"

    def stats(self) -> Dict:
        return {
            "temperature_k": self.temperature_k,
            "peak_wavelength_nm": round(self.peak_wavelength_nm(), 2),
            "total_flux_w_m2": f"{self.total_flux_w_m2():.2e}",
            "luminosity_w": f"{self.luminosity_w():.2e}",
            "solar_luminosities": round(self.solar_luminosity(), 4),
            "color": self.color_index_approx(),
        }

def run():
    bb = BlackbodyCalculator(temperature_k=5778, radius_m=6.96e8)
    print(bb.stats())

if __name__ == "__main__":
    run()
