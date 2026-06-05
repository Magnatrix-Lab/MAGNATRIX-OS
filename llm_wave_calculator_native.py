"""Native stdlib module: Wave Calculator
Calculates wave height, period, wavelength, and energy.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class WaveCalculator:
    wave_height_m: float
    wave_period_s: float
    water_depth_m: float = 100.0

    def wavelength_m(self) -> float:
        g = 9.81
        if self.water_depth_m > self.wavelength_deep_m() / 2:
            return self.wavelength_deep_m()
        t = self.wave_period_s
        return (g * t ** 2) / (2 * math.pi) * math.tanh(2 * math.pi * self.water_depth_m / ((g * t ** 2) / (2 * math.pi)))

    def wavelength_deep_m(self) -> float:
        g = 9.81
        return (g * self.wave_period_s ** 2) / (2 * math.pi)

    def wave_speed_m_s(self) -> float:
        if self.wave_period_s == 0:
            return 0.0
        return self.wavelength_m() / self.wave_period_s

    def wave_energy_j_m2(self) -> float:
        return 0.125 * 1025 * 9.81 * self.wave_height_m ** 2

    def wave_power_kw_m(self) -> float:
        return (self.wave_energy_j_m2() * self.wave_speed_m_s()) / 1000

    def wave_steepness(self) -> float:
        wl = self.wavelength_m()
        if wl == 0:
            return 0.0
        return self.wave_height_m / wl

    def breaking_depth_m(self) -> float:
        return self.wave_height_m / 0.78

    def stats(self) -> Dict:
        return {
            "wave_height_m": self.wave_height_m,
            "wave_period_s": self.wave_period_s,
            "water_depth_m": self.water_depth_m,
            "wavelength_m": round(self.wavelength_m(), 2),
            "wave_speed_m_s": round(self.wave_speed_m_s(), 2),
            "wave_energy_j_m2": round(self.wave_energy_j_m2(), 1),
            "wave_power_kw_m": round(self.wave_power_kw_m(), 3),
            "wave_steepness": round(self.wave_steepness(), 4),
        }

def run():
    wc = WaveCalculator(wave_height_m=2.5, wave_period_s=8, water_depth_m=50)
    print(wc.stats())

if __name__ == "__main__":
    run()
