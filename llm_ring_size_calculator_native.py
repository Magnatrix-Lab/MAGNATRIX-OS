"""Native stdlib module: Ring Size Calculator
Converts ring sizes, calculates diameter, circumference, and mandrel sizes.
"""
from dataclasses import dataclass
from typing import Dict, Optional
import math

@dataclass
class RingSizeCalculator:
    size_us: Optional[float] = None
    size_uk: Optional[str] = None
    size_eu: Optional[float] = None
    circumference_mm: Optional[float] = None
    diameter_mm: Optional[float] = None

    _US_TO_MM = {5: 15.7, 6: 16.5, 7: 17.3, 8: 18.1, 9: 18.9, 10: 19.8, 11: 20.6, 12: 21.4, 13: 22.2}

    def _get_circumference(self) -> float:
        if self.circumference_mm is not None:
            return self.circumference_mm
        if self.diameter_mm is not None:
            return self.diameter_mm * math.pi
        if self.size_us is not None:
            return self._US_TO_MM.get(self.size_us, 17.3) * math.pi
        if self.size_eu is not None:
            return self.size_eu
        return 54.0

    def _get_diameter(self) -> float:
        return self._get_circumference() / math.pi

    def us_size(self) -> float:
        circ = self._get_circumference()
        return round((circ - 36.5) / 2.55, 1)

    def uk_size(self) -> str:
        us = self.us_size()
        uk = round(us - 0.5, 1)
        return f"{uk}"

    def eu_size(self) -> float:
        return round(self._get_circumference(), 1)

    def inner_diameter_mm(self) -> float:
        return round(self._get_diameter(), 1)

    def inner_circumference_mm(self) -> float:
        return round(self._get_circumference(), 1)

    def metal_needed_mm(self, band_width_mm: float, band_thickness_mm: float) -> float:
        return 2 * math.pi * (self._get_diameter() / 2 + band_thickness_mm / 2) * band_width_mm * band_thickness_mm

    def stats(self, band_width_mm: float = 4.0, band_thickness_mm: float = 1.5) -> Dict:
        return {
            "us_size": self.us_size(),
            "uk_size": self.uk_size(),
            "eu_size": self.eu_size(),
            "inner_diameter_mm": self.inner_diameter_mm(),
            "inner_circumference_mm": self.inner_circumference_mm(),
            "metal_needed_mm3": round(self.metal_needed_mm(band_width_mm, band_thickness_mm), 1),
        }

def run():
    rsc = RingSizeCalculator(size_us=7)
    print(rsc.stats())

if __name__ == "__main__":
    run()
