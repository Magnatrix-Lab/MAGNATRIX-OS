"""Exposure Calculator — EV, stops, ND filters, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class ExposureCalculator:
    aperture: float = 5.6
    shutter: float = 1.0 / 125.0
    iso: float = 100.0

    def ev(self) -> float:
        return math.log2(self.aperture * self.aperture / self.shutter) - math.log2(self.iso / 100)

    def exposure_value(self) -> float:
        return self.ev()

    def stops_difference(self, other: 'ExposureCalculator') -> float:
        return self.ev() - other.ev()

    def nd_filter_required(self, target_shutter: float) -> float:
        if self.shutter <= 0 or target_shutter <= 0:
            return 0.0
        ratio = target_shutter / self.shutter
        return math.log2(ratio) if ratio > 0 else 0.0

    def reciprocity_failure(self, actual_shutter: float, factor: float = 1.2) -> float:
        if actual_shutter <= 1:
            return actual_shutter
        return actual_shutter ** factor

    def sunny_16_shutter(self) -> float:
        return 1.0 / self.iso

    def stats(self) -> Dict:
        return {"ev": round(self.ev(), 2), "shutter": self.shutter, "aperture": self.aperture, "iso": self.iso}

def run():
    ec = ExposureCalculator(aperture=2.8, shutter=1/500, iso=400)
    print(ec.stats())
    print("Sunny 16 shutter:", ec.sunny_16_shutter())
    print("ND for 1s:", ec.nd_filter_required(1.0))

if __name__ == "__main__":
    run()
