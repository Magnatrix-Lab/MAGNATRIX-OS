"""Plant Growth — GDD, leaf area, biomass, photosynthesis, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class PlantGrowth:
    base_temp: float = 10.0
    max_temp: float = 35.0
    temps: List[float] = field(default_factory=list)

    def growing_degree_days(self) -> float:
        gdd = 0.0
        for t in self.temps:
            eff = max(0, min(t, self.max_temp) - self.base_temp)
            gdd += eff
        return gdd

    def leaf_area_index(self, leaf_area: float, ground_area: float) -> float:
        return leaf_area / ground_area if ground_area > 0 else 0.0

    def relative_growth_rate(self, w1: float, w2: float, days: int) -> float:
        if w1 <= 0 or w2 <= 0 or days <= 0:
            return 0.0
        return (math.log(w2) - math.log(w1)) / days

    def net_photosynthesis(self, light: float, co2: float, temp: float) -> float:
        if temp < self.base_temp or temp > self.max_temp:
            return 0.0
        return light * 0.05 * co2 / 400 * (1 - abs(temp - 25) / 30)

    def stats(self) -> Dict:
        return {"gdd": round(self.growing_degree_days(), 1), "temp_count": len(self.temps)}

def run():
    import math
    pg = PlantGrowth(temps=[15, 18, 22, 25, 20, 16, 14])
    print(pg.stats())
    print("LAI:", pg.leaf_area_index(50, 10))
    print("RGR:", pg.relative_growth_rate(10, 25, 30))

if __name__ == "__main__":
    run()
