"""Tea Steep — temp, time, leaf ratio, infusions, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class TeaSteep:
    tea_type: str = "green"
    leaf_g: float = 3.0
    water_ml: float = 150.0

    def recommended_temp(self) -> float:
        temps = {"green": 80, "white": 75, "oolong": 90, "black": 95, "puerh": 100}
        return temps.get(self.tea_type, 85)

    def recommended_time(self) -> float:
        times = {"green": 2, "white": 3, "oolong": 3, "black": 4, "puerh": 5}
        return times.get(self.tea_type, 3)

    def leaf_ratio(self) -> float:
        return self.leaf_g / self.water_ml if self.water_ml > 0 else 0.0

    def infusions_estimate(self) -> int:
        counts = {"green": 3, "white": 3, "oolong": 5, "black": 2, "puerh": 10}
        return counts.get(self.tea_type, 3)

    def gongfu_ratio(self) -> float:
        return 1.0 / 15.0

    def western_ratio(self) -> float:
        return 1.0 / 50.0

    def stats(self) -> Dict:
        return {"temp": self.recommended_temp(), "time": self.recommended_time(), "infusions": self.infusions_estimate(), "ratio": round(self.leaf_ratio(), 4)}

def run():
    ts = TeaSteep("oolong", 5, 100)
    print(ts.stats())

if __name__ == "__main__":
    run()
