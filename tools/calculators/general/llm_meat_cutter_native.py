"""Native stdlib module: Meat Cutter / Yield Calculator
Calculates primal/sub-primal yield percentages, cutting loss, and portion sizing.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class CarcassType(Enum):
    BEEF = "beef"
    PORK = "pork"
    LAMB = "lamb"
    VEAL = "veal"

@dataclass
class PrimalCut:
    name: str
    weight_kg: float
    yield_pct: float

@dataclass
class MeatCutter:
    carcass_type: CarcassType
    live_weight_kg: float
    dressing_pct: float = 0.62
    primals: List[PrimalCut] = field(default_factory=list)

    def hot_carcass_weight(self) -> float:
        return self.live_weight_kg * self.dressing_pct

    def cold_carcass_weight(self, shrink_pct: float = 0.02) -> float:
        return self.hot_carcass_weight() * (1 - shrink_pct)

    def total_yield_kg(self) -> float:
        return sum(p.weight_kg * (p.yield_pct / 100) for p in self.primals)

    def cutting_loss_pct(self) -> float:
        ccw = self.cold_carcass_weight()
        if ccw == 0:
            return 0.0
        return ((ccw - self.total_yield_kg()) / ccw) * 100

    def stats(self) -> Dict[str, float]:
        return {
            "hot_carcass_kg": round(self.hot_carcass_weight(), 2),
            "cold_carcass_kg": round(self.cold_carcass_weight(), 2),
            "total_yield_kg": round(self.total_yield_kg(), 2),
            "cutting_loss_pct": round(self.cutting_loss_pct(), 2),
        }

def run():
    cutter = MeatCutter(
        carcass_type=CarcassType.BEEF,
        live_weight_kg=450,
        dressing_pct=0.64,
        primals=[
            PrimalCut("chuck", 120, 75),
            PrimalCut("rib", 45, 80),
            PrimalCut("loin", 55, 82),
            PrimalCut("round", 70, 78),
        ]
    )
    print(cutter.stats())

if __name__ == "__main__":
    run()
