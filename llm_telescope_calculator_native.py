"""Native stdlib module: Telescope Calculator
Calculates magnification, resolution, and light-gathering power for telescopes.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class TelescopeCalculator:
    aperture_mm: float
    focal_length_mm: float
    eyepiece_focal_length_mm: float
    wavelength_nm: float = 550

    def magnification(self) -> float:
        if self.eyepiece_focal_length_mm == 0:
            return 0.0
        return self.focal_length_mm / self.eyepiece_focal_length_mm

    def f_ratio(self) -> float:
        if self.aperture_mm == 0:
            return 0.0
        return self.focal_length_mm / self.aperture_mm

    def resolving_power_arcsec(self) -> float:
        if self.aperture_mm == 0:
            return 0.0
        return 116 / self.aperture_mm

    def dawes_limit_arcsec(self) -> float:
        if self.aperture_mm == 0:
            return 0.0
        return 116 / self.aperture_mm

    def light_gathering_power(self, pupil_diameter_mm: float = 7) -> float:
        if pupil_diameter_mm == 0:
            return 0.0
        return (self.aperture_mm / pupil_diameter_mm) ** 2

    def field_of_view_deg(self, eyepiece_fov_deg: float = 50) -> float:
        mag = self.magnification()
        if mag == 0:
            return 0.0
        return eyepiece_fov_deg / mag

    def limiting_magnitude(self) -> float:
        if self.aperture_mm == 0:
            return 0.0
        return 7.5 + 5 * math.log10(self.aperture_mm / 10)

    def stats(self) -> Dict:
        return {
            "aperture_mm": self.aperture_mm,
            "focal_length_mm": self.focal_length_mm,
            "eyepiece_mm": self.eyepiece_focal_length_mm,
            "magnification": round(self.magnification(), 1),
            "f_ratio": round(self.f_ratio(), 1),
            "resolving_power_arcsec": round(self.resolving_power_arcsec(), 2),
            "light_gathering": round(self.light_gathering_power(), 1),
            "limiting_magnitude": round(self.limiting_magnitude(), 2),
        }

def run():
    tc = TelescopeCalculator(aperture_mm=200, focal_length_mm=1000, eyepiece_focal_length_mm=25)
    print(tc.stats())

if __name__ == "__main__":
    run()
