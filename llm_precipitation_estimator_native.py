"""Precipitation Estimator — radar reflectivity, rain rate, accumulation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class PrecipitationEstimator:
    reflectivity_dbz: List[float] = field(default_factory=list)

    def zr_relation(self, z: float) -> float:
        """Marshall-Palmer: Z = 200 R^1.6"""
        return (z / 200) ** (1 / 1.6)

    def dbz_to_z(self, dbz: float) -> float:
        return 10 ** (dbz / 10)

    def rain_rate(self, dbz: float) -> float:
        if dbz < 0:
            return 0.0
        return self.zr_relation(self.dbz_to_z(dbz))

    def accumulation(self, duration_hours: float) -> float:
        return sum(self.rain_rate(d) for d in self.reflectivity_dbz) / len(self.reflectivity_dbz) * duration_hours if self.reflectivity_dbz else 0

    def intensity_category(self, dbz: float) -> str:
        if dbz < 20:
            return "light"
        elif dbz < 40:
            return "moderate"
        elif dbz < 50:
            return "heavy"
        return "severe"

    def stats(self) -> Dict:
        rates = [self.rain_rate(d) for d in self.reflectivity_dbz]
        return {"max_dbz": max(self.reflectivity_dbz) if self.reflectivity_dbz else 0, "mean_rate": round(sum(rates)/len(rates), 2) if rates else 0}

def run():
    pe = PrecipitationEstimator([15, 25, 35, 45])
    print(pe.stats())
    print("Accumulation 1h:", pe.accumulation(1))

if __name__ == "__main__":
    run()
