"""Nougat Whip — sugar concentration, whipping temp, aeration, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class NougatWhip:
    sugar_temp: float = 140.0
    whipping_speed: int = 500
    egg_white_pct: float = 15.0
    honey_pct: float = 20.0
    nut_pct: float = 30.0

    def sugar_concentration(self) -> float:
        return 100 - (150 - self.sugar_temp) * 0.5

    def aeration_pct(self) -> float:
        return min(60, self.whipping_speed / 10 + self.egg_white_pct * 1.5)

    def density_estimate(self) -> float:
        return 1.2 - self.aeration_pct() * 0.01

    def set_time_min(self) -> int:
        return int(30 + (self.sugar_temp - 120) * 0.3)

    def cutting_temp(self) -> float:
        return 30

    def stats(self) -> Dict:
        return {"concentration": round(self.sugar_concentration(), 1), "aeration": round(self.aeration_pct(), 1), "density": round(self.density_estimate(), 3), "set_time": self.set_time_min()}

def run():
    nw = NougatWhip(sugar_temp=145, whipping_speed=600, egg_white_pct=20, honey_pct=15, nut_pct=35)
    print(nw.stats())

if __name__ == "__main__":
    run()
