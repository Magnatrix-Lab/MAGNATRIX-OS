"""Current Profiler — velocity, direction, shear, transport, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class CurrentProfiler:
    velocities: List[Tuple[float, float]] = field(default_factory=list)
    """u, v components at depths"""
    depths: List[float] = field(default_factory=list)

    def speed(self, u: float, v: float) -> float:
        return math.sqrt(u**2 + v**2)

    def direction(self, u: float, v: float) -> float:
        d = math.degrees(math.atan2(v, u))
        return d if d >= 0 else d + 360

    def shear(self) -> List[float]:
        if len(self.depths) < 2:
            return []
        shears = []
        for i in range(len(self.depths) - 1):
            s1 = self.speed(*self.velocities[i])
            s2 = self.speed(*self.velocities[i+1])
            dz = self.depths[i+1] - self.depths[i]
            shears.append((s2 - s1) / dz if dz > 0 else 0)
        return shears

    def transport(self, width: float) -> float:
        total = 0.0
        for i in range(len(self.depths) - 1):
            s = self.speed(*self.velocities[i])
            dz = self.depths[i+1] - self.depths[i]
            total += s * dz * width
        return total

    def stats(self) -> Dict:
        speeds = [self.speed(u, v) for u, v in self.velocities]
        return {"layers": len(self.velocities), "max_speed": max(speeds) if speeds else 0, "mean_speed": sum(speeds)/len(speeds) if speeds else 0}

def run():
    cp = CurrentProfiler(velocities=[(0.5,0.3),(0.3,0.2),(0.1,0.1)], depths=[0,10,20])
    print(cp.stats())
    print("Shear:", cp.shear())
    print("Transport:", cp.transport(100))

if __name__ == "__main__":
    run()
