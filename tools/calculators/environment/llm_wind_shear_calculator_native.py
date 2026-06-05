"""Wind Shear Calculator — microburst, gust front, LLWS, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class WindShearCalculator:
    wind_speeds: List[float] = field(default_factory=list)
    heights: List[float] = field(default_factory=list)

    def shear(self, layer: int) -> float:
        if len(self.wind_speeds) < 2 or layer >= len(self.wind_speeds) - 1:
            return 0.0
        dv = self.wind_speeds[layer+1] - self.wind_speeds[layer]
        dh = self.heights[layer+1] - self.heights[layer]
        return dv / dh if dh > 0 else 0.0

    def shear_profile(self) -> List[float]:
        return [self.shear(i) for i in range(len(self.wind_speeds) - 1)]

    def microburst_risk(self, threshold: float = 10.0) -> bool:
        return max(self.shear_profile(), default=0) > threshold

    def headwind_change(self, distance: float) -> float:
        if len(self.wind_speeds) < 2:
            return 0.0
        return (self.wind_speeds[-1] - self.wind_speeds[0]) / distance * 1000 if distance > 0 else 0.0

    def stats(self) -> Dict:
        return {"max_shear": round(max(self.shear_profile(), default=0), 2), "microburst_risk": self.microburst_risk()}

def run():
    wsc = WindShearCalculator(wind_speeds=[10, 15, 25, 40], heights=[0, 100, 200, 300])
    print(wsc.stats())
    print("Headwind change:", wsc.headwind_change(1000))

if __name__ == "__main__":
    run()
