"""Deforestation Tracker — change detection, rate, drivers, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class DeforestationTracker:
    forest_area: List[float] = field(default_factory=list)
    """Area in hectares over years"""
    years: List[int] = field(default_factory=list)

    def annual_loss(self) -> List[float]:
        return [self.forest_area[i] - self.forest_area[i+1] for i in range(len(self.forest_area)-1)]

    def annual_rate(self) -> List[float]:
        if len(self.forest_area) < 2:
            return []
        return [(self.forest_area[i] - self.forest_area[i+1]) / self.forest_area[i] * 100 for i in range(len(self.forest_area)-1)]

    def total_loss(self) -> float:
        if not self.forest_area:
            return 0.0
        return self.forest_area[0] - self.forest_area[-1]

    def cumulative_loss(self) -> List[float]:
        loss = []
        cum = 0.0
        for i in range(len(self.forest_area) - 1):
            cum += self.forest_area[i] - self.forest_area[i+1]
            loss.append(cum)
        return loss

    def halving_time(self) -> float:
        rates = self.annual_rate()
        if not rates:
            return 0.0
        avg_rate = sum(rates) / len(rates) / 100
        if avg_rate <= 0:
            return float('inf')
        return 0.693 / avg_rate

    def stats(self) -> Dict:
        return {"total_loss": round(self.total_loss(), 0), "avg_rate": round(sum(self.annual_rate())/len(self.annual_rate()) if self.annual_rate() else 0, 2), "halving_time": round(self.halving_time(), 1)}

def run():
    dt = DeforestationTracker(forest_area=[100000, 98000, 95000, 90000, 85000], years=[2020, 2021, 2022, 2023, 2024])
    print(dt.stats())
    print("Annual loss:", dt.annual_loss())
    print("Cumulative:", dt.cumulative_loss())

if __name__ == "__main__":
    run()
