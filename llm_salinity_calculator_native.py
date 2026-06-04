"""Salinity Calculator — conductivity, PSU, mixing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class SalinityCalculator:
    conductivity: float = 42.0
    temperature: float = 25.0
    pressure: float = 0.0

    def salinity_psu(self) -> float:
        """Simplified from UNESCO 1981."""
        R = self.conductivity / 42.914
        return round(0.008 + 25.385 * R + 14.094 * R**2 - 7.026 * R**3 + 2.708 * R**4, 3)

    def density(self) -> float:
        s = self.salinity_psu()
        t = self.temperature
        return 1028 - 0.125 * t + 0.78 * s / 1000

    def mixing(self, s1: float, v1: float, s2: float, v2: float) -> float:
        total_v = v1 + v2
        if total_v == 0:
            return 0.0
        return (s1 * v1 + s2 * v2) / total_v

    def halocline(self, profile: List[Tuple[float, float]]) -> float:
        if len(profile) < 2:
            return 0.0
        max_grad = 0.0
        depth = 0.0
        for i in range(len(profile) - 1):
            dz = profile[i+1][0] - profile[i][0]
            ds = profile[i+1][1] - profile[i][1]
            grad = abs(ds / dz) if dz > 0 else 0
            if grad > max_grad:
                max_grad = grad
                depth = (profile[i][0] + profile[i+1][0]) / 2
        return depth

    def stats(self) -> Dict:
        return {"salinity_psu": self.salinity_psu(), "density": round(self.density(), 3)}

def run():
    sc = SalinityCalculator(conductivity=50)
    print(sc.stats())
    print("Mixing:", sc.mixing(35, 100, 30, 50))

if __name__ == "__main__":
    run()
