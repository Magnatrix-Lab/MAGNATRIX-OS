"""Periodontal Calculator — probing depth, CAL, bone loss, staging, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class PeriodontalCalculator:
    probing_depths: List[float] = field(default_factory=list)
    recession: List[float] = field(default_factory=list)
    tooth_lengths: List[float] = field(default_factory=list)

    def clinical_attachment_loss(self, site: int) -> float:
        if site >= len(self.probing_depths) or site >= len(self.recession):
            return 0.0
        return self.probing_depths[site] + self.recession[site]

    def bone_loss_pct(self, site: int) -> float:
        cal = self.clinical_attachment_loss(site)
        if site >= len(self.tooth_lengths) or self.tooth_lengths[site] == 0:
            return 0.0
        return (cal / self.tooth_lengths[site]) * 100

    def stage(self, site: int) -> str:
        cal = self.clinical_attachment_loss(site)
        if cal <= 1: return "healthy"
        elif cal <= 3: return "stage I"
        elif cal <= 4: return "stage II"
        elif cal <= 5: return "stage III"
        return "stage IV"

    def average_pd(self) -> float:
        return sum(self.probing_depths) / len(self.probing_depths) if self.probing_depths else 0.0

    def sites_at_risk(self, threshold: float = 5.0) -> int:
        return sum(1 for pd in self.probing_depths if pd >= threshold)

    def stats(self) -> Dict:
        if not self.probing_depths:
            return {}
        return {
            "avg_pd": round(self.average_pd(), 2),
            "max_cal": round(max(self.clinical_attachment_loss(i) for i in range(len(self.probing_depths))), 2),
            "sites_at_risk": self.sites_at_risk(),
            "worst_stage": max(self.stage(i) for i in range(len(self.probing_depths)))
        }

def run():
    pc = PeriodontalCalculator(probing_depths=[3, 4, 5, 6, 3], recession=[0, 1, 2, 2, 0], tooth_lengths=[12, 12, 12, 12, 12])
    print(pc.stats())
    for i in range(len(pc.probing_depths)):
        print(f"Site {i}: CAL={pc.clinical_attachment_loss(i):.1f}, stage={pc.stage(i)}")

if __name__ == "__main__":
    run()
