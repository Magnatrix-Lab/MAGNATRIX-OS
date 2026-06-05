"""Native stdlib module: Warp Length Calculator
Calculates warp length, take-up, shrinkage, and loom waste for weaving.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class WarpLengthCalculator:
    finished_length_m: float
    loom_waste_m: float = 0.6
    take_up_pct: float = 10.0
    shrinkage_pct: float = 8.0
    fringe_m: float = 0.0
    ends_count: int = 300

    def warp_length_m(self) -> float:
        base = self.finished_length_m / (1 - self.take_up_pct / 100) / (1 - self.shrinkage_pct / 100)
        return base + self.loom_waste_m + self.fringe_m

    def total_warp_yarn_m(self) -> float:
        return self.warp_length_m() * self.ends_count

    def total_warp_yarn_km(self) -> float:
        return self.total_warp_yarn_m() / 1000

    def waste_pct(self) -> float:
        if self.warp_length_m() == 0:
            return 0
        return (self.loom_waste_m / self.warp_length_m()) * 100

    def warp_weight_g(self, yarn_tex: float = 20.0) -> float:
        return self.total_warp_yarn_m() * yarn_tex / 1000

    def stats(self, yarn_tex: float = 20.0) -> Dict:
        return {
            "finished_length_m": self.finished_length_m,
            "warp_length_m": round(self.warp_length_m(), 2),
            "total_warp_yarn_m": round(self.total_warp_yarn_m(), 1),
            "total_warp_yarn_km": round(self.total_warp_yarn_km(), 2),
            "waste_pct": round(self.waste_pct(), 1),
            "warp_weight_g": round(self.warp_weight_g(yarn_tex), 1),
            "ends_count": self.ends_count,
        }

def run():
    wlc = WarpLengthCalculator(finished_length_m=2.5, loom_waste_m=0.7, take_up_pct=12, shrinkage_pct=10, fringe_m=0.2, ends_count=400)
    print(wlc.stats())

if __name__ == "__main__":
    run()
