"""Native stdlib module: Radar Range Calculator
Calculates radar detection ranges, resolution, and power requirements.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class RadarRangeCalculator:
    transmit_power_w: float
    antenna_gain_db: float
    frequency_ghz: float
    target_rcs_m2: float
    min_detectable_signal_dbm: float = -120

    def wavelength_m(self) -> float:
        c = 3e8
        return c / (self.frequency_ghz * 1e9)

    def max_range_m(self) -> float:
        g = 10 ** (self.antenna_gain_db / 10)
        lam = self.wavelength_m()
        p_t = self.transmit_power_w
        s_min = 10 ** (self.min_detectable_signal_dbm / 10) / 1000
        if s_min == 0:
            return 0.0
        return ((p_t * g ** 2 * lam ** 2 * self.target_rcs_m2) / ((4 * math.pi) ** 3 * s_min)) ** 0.25

    def max_range_km(self) -> float:
        return self.max_range_m() / 1000

    def range_resolution_m(self, bandwidth_mhz: float = 10) -> float:
        c = 3e8
        return c / (2 * bandwidth_mhz * 1e6)

    def angular_resolution_deg(self, aperture_m: float = 2) -> float:
        if aperture_m == 0:
            return 0.0
        return math.degrees(self.wavelength_m() / aperture_m)

    def pulse_repetition_frequency_hz(self, max_range_km: float = 0) -> float:
        r = max_range_km if max_range_km else self.max_range_km()
        if r == 0:
            return 0.0
        return 3e8 / (2 * r * 1000)

    def stats(self, bandwidth_mhz: float = 10, aperture_m: float = 2) -> Dict:
        return {
            "frequency_ghz": self.frequency_ghz,
            "max_range_km": round(self.max_range_km(), 1),
            "range_resolution_m": round(self.range_resolution_m(bandwidth_mhz), 1),
            "angular_resolution_deg": round(self.angular_resolution_deg(aperture_m), 3),
            "prf_hz": round(self.pulse_repetition_frequency_hz(), 1),
        }

def run():
    rrc = RadarRangeCalculator(transmit_power_w=1000, antenna_gain_db=30, frequency_ghz=10, target_rcs_m2=5)
    print(rrc.stats())

if __name__ == "__main__":
    run()
