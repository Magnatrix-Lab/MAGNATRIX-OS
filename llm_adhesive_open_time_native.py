"""Adhesive Open Time Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class AdhesiveOpenTime:
    adhesive_type: str
    temperature_c: float
    humidity_percent: float = 50.0
    substrate_absorbency: str = "medium"
    film_thickness_mm: float = 0.2

    def base_open_time_minutes(self) -> float:
        times = {"pva": 10, "pu": 20, "epoxy": 30, "contact": 15, "hot_melt": 3, "cyanoacrylate": 1}
        return times.get(self.adhesive_type, 15)

    def temperature_factor(self) -> float:
        return max(0.2, math.exp((25 - self.temperature_c) / 10.0))

    def humidity_factor(self) -> float:
        return max(0.5, 1.0 - (self.humidity_percent - 50) / 100.0)

    def absorbency_factor(self) -> float:
        factors = {"low": 1.2, "medium": 1.0, "high": 0.7, "very_high": 0.5}
        return factors.get(self.substrate_absorbency, 1.0)

    def thickness_factor(self) -> float:
        return max(0.5, self.film_thickness_mm / 0.2)

    def open_time_minutes(self) -> float:
        return round(self.base_open_time_minutes() * self.temperature_factor() * 
                     self.humidity_factor() * self.absorbency_factor() * self.thickness_factor(), 1)

    def working_time_minutes(self) -> float:
        return round(self.open_time_minutes() * 0.8, 1)

    def clamp_time_minutes(self) -> float:
        clamp = {"pva": 30, "pu": 60, "epoxy": 120, "contact": 5, "hot_melt": 1, "cyanoacrylate": 0.5}
        return round(clamp.get(self.adhesive_type, 30) * self.temperature_factor(), 1)

    def stats(self) -> Dict[str, float]:
        return {
            "open_time_minutes": self.open_time_minutes(),
            "working_time_minutes": self.working_time_minutes(),
            "clamp_time_minutes": self.clamp_time_minutes(),
        }

    def run(self):
        print("=" * 60)
        print("ADHESIVE OPEN TIME CALCULATOR")
        print("=" * 60)
        ad = AdhesiveOpenTime(
            adhesive_type="pu", temperature_c=30, humidity_percent=60,
            substrate_absorbency="medium", film_thickness_mm=0.25
        )
        print(f"Adhesive: {ad.adhesive_type}")
        print(f"Temperature: {ad.temperature_c} C")
        print(f"Humidity: {ad.humidity_percent}%")
        print(f"Open time: {ad.open_time_minutes():.1f} min")
        print(f"Working time: {ad.working_time_minutes():.1f} min")
        print(f"Clamp time: {ad.clamp_time_minutes():.1f} min")
        print(f"Stats: {ad.stats()}")

if __name__ == "__main__":
    AdhesiveOpenTime("pva", 25).run()
