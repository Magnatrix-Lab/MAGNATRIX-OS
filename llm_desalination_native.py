"""Desalination Calculator -- RO, energy, recovery, brine, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class DesalinationCalculator:
    feed_tds_mg_l: float = 35000.0
    permeate_tds_mg_l: float = 500.0
    recovery_pct: float = 45.0
    feed_flow_m3_day: float = 10000.0
    energy_kwh_m3: float = 3.5

    def permeate_flow(self) -> float:
        return self.feed_flow_m3_day * self.recovery_pct / 100

    def brine_flow(self) -> float:
        return self.feed_flow_m3_day - self.permeate_flow()

    def brine_tds(self) -> float:
        if self.brine_flow() <= 0:
            return 0.0
        return self.feed_tds_mg_l * self.feed_flow_m3_day / self.brine_flow()

    def total_energy(self) -> float:
        return self.permeate_flow() * self.energy_kwh_m3

    def salt_rejection(self) -> float:
        return (1 - self.permeate_tds_mg_l / self.feed_tds_mg_l) * 100

    def specific_energy(self) -> float:
        return self.energy_kwh_m3

    def stats(self) -> Dict:
        return {"permeate_m3_d": round(self.permeate_flow(), 0), "brine_m3_d": round(self.brine_flow(), 0), "brine_tds": round(self.brine_tds(), 0), "energy_mwh_d": round(self.total_energy() / 1000, 1), "rejection": round(self.salt_rejection(), 1)}

def run():
    dc = DesalinationCalculator()
    print(dc.stats())

if __name__ == "__main__":
    run()
