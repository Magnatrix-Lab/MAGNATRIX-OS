"""Wind Profiler — shear, gust, power law, turbulence, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class WindProfiler:
    speeds: List[float] = field(default_factory=list)
    directions: List[float] = field(default_factory=list)
    heights: List[float] = field(default_factory=list)

    def power_law(self, z: float, z0: float, u0: float, alpha: float = 0.14) -> float:
        return u0 * (z / z0) ** alpha

    def wind_shear(self) -> List[float]:
        if len(self.heights) < 2:
            return []
        shears = []
        for i in range(len(self.heights) - 1):
            dz = self.heights[i+1] - self.heights[i]
            du = self.speeds[i+1] - self.speeds[i]
            shears.append(du / dz if dz > 0 else 0)
        return shears

    def gust_factor(self, gust: float, sustained: float) -> float:
        return gust / sustained if sustained > 0 else 1.0

    def turbulence(self) -> float:
        if len(self.speeds) < 2:
            return 0.0
        mean = sum(self.speeds) / len(self.speeds)
        var = sum((s - mean)**2 for s in self.speeds) / len(self.speeds)
        return math.sqrt(var) / mean if mean > 0 else 0.0

    def wind_power_density(self, rho: float = 1.225) -> List[float]:
        return [0.5 * rho * s**3 for s in self.speeds]

    def stats(self) -> Dict:
        return {"max_speed": max(self.speeds) if self.speeds else 0, "mean_speed": sum(self.speeds)/len(self.speeds) if self.speeds else 0, "turbulence": round(self.turbulence(), 3)}

def run():
    wp = WindProfiler(speeds=[5,7,10,12], heights=[10,20,50,100])
    print(wp.stats())
    print("Shear:", wp.wind_shear())
    print("Power density:", wp.wind_power_density())

if __name__ == "__main__":
    run()
