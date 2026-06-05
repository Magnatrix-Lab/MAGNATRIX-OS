"""Hop Utilization — IBU, alpha acid, boil time, gravity, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class HopUtilization:
    alpha_acid_pct: float = 5.0
    weight_g: float = 30.0
    boil_time_min: float = 60.0
    wort_gravity: float = 1.050
    volume_l: float = 20.0

    def utilization_rager(self) -> float:
        g = self.wort_gravity - 1.0
        util = 18.11 + 13.86 * math.tanh((self.boil_time_min - 31.32) / 18.27)
        util /= 1 + 1.5 * g
        return util / 100

    def utilization_tinseth(self) -> float:
        g = self.wort_gravity - 1.0
        bigness = 1.65 * 0.000125 ** g
        boil = (1 - math.exp(-0.04 * self.boil_time_min)) / 4.15
        return bigness * boil

    def ibu(self, method: str = "tinseth") -> float:
        util = self.utilization_tinseth() if method == "tinseth" else self.utilization_rager()
        return self.alpha_acid_pct * self.weight_g * util * 1000 / self.volume_l

    def stats(self) -> Dict:
        return {"rager_util": round(self.utilization_rager(), 3), "tinseth_util": round(self.utilization_tinseth(), 3), "ibu_rager": round(self.ibu("rager"), 1), "ibu_tinseth": round(self.ibu(), 1)}

def run():
    hu = HopUtilization(alpha_acid_pct=12, weight_g=50, boil_time_min=30, wort_gravity=1.070, volume_l=25)
    print(hu.stats())

if __name__ == "__main__":
    run()
