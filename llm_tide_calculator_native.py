"""Native stdlib module: Tide Calculator
Calculates tidal heights, ranges, and harmonic constituents.
"""
from dataclasses import dataclass, field
from typing import List, Dict
import math

@dataclass
class HarmonicConstituent:
    name: str
    amplitude_m: float
    phase_deg: float
    speed_deg_per_hour: float

@dataclass
class TideCalculator:
    location_name: str
    mean_sea_level_m: float
    constituents: List[HarmonicConstituent] = field(default_factory=list)

    def tidal_range_m(self) -> float:
        if not self.constituents:
            return 0.0
        max_amp = sum(c.amplitude_m for c in self.constituents)
        return 2 * max_amp

    def tidal_height_at_time(self, hours_since_epoch: float) -> float:
        height = self.mean_sea_level_m
        for c in self.constituents:
            angle = math.radians(c.speed_deg_per_hour * hours_since_epoch + c.phase_deg)
            height += c.amplitude_m * math.cos(angle)
        return height

    def high_tide_estimate_m(self) -> float:
        return self.mean_sea_level_m + sum(c.amplitude_m for c in self.constituents)

    def low_tide_estimate_m(self) -> float:
        return self.mean_sea_level_m - sum(c.amplitude_m for c in self.constituents)

    def spring_range_m(self) -> float:
        return 2 * sum(c.amplitude_m for c in self.constituents)

    def neap_range_m(self) -> float:
        if len(self.constituents) < 2:
            return self.spring_range_m()
        m2 = next((c.amplitude_m for c in self.constituents if c.name == "M2"), 0)
        s2 = next((c.amplitude_m for c in self.constituents if c.name == "S2"), 0)
        return 2 * (m2 - s2)

    def stats(self) -> Dict:
        return {
            "location": self.location_name,
            "msl_m": self.mean_sea_level_m,
            "tidal_range_m": round(self.tidal_range_m(), 2),
            "high_tide_m": round(self.high_tide_estimate_m(), 2),
            "low_tide_m": round(self.low_tide_estimate_m(), 2),
            "spring_range_m": round(self.spring_range_m(), 2),
            "neap_range_m": round(self.neap_range_m(), 2),
            "constituents": len(self.constituents),
        }

def run():
    tc = TideCalculator(
        location_name="Port A",
        mean_sea_level_m=2.5,
        constituents=[
            HarmonicConstituent("M2", 1.2, 0, 28.984),
            HarmonicConstituent("S2", 0.4, 30, 30.0),
            HarmonicConstituent("K1", 0.3, 60, 15.041),
        ]
    )
    print(tc.stats())

if __name__ == "__main__":
    run()
