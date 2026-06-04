"""Training Planner — periodization, load, recovery, taper, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class TrainingPlanner:
    base_volume: float = 100.0
    weeks: int = 12
    peak_week: int = 10

    def periodization(self) -> List[float]:
        plan = []
        for week in range(1, self.weeks + 1):
            if week <= self.peak_week:
                load = self.base_volume * (0.7 + 0.3 * week / self.peak_week)
            elif week == self.peak_week + 1:
                load = self.base_volume * 1.1
            else:
                load = self.base_volume * (1.1 - 0.2 * (week - self.peak_week - 1))
            plan.append(round(load, 1))
        return plan

    def recovery_needed(self, load: float, fatigue: float) -> bool:
        return fatigue > 0.7 or load > self.base_volume * 1.2

    def taper(self, volumes: List[float], taper_weeks: int = 2) -> List[float]:
        peak = max(volumes) if volumes else 0
        return [peak * (1 - 0.3 * i / taper_weeks) for i in range(1, taper_weeks + 1)]

    def acwr(self, acute: float, chronic: float) -> float:
        return acute / chronic if chronic > 0 else 0.0

    def stats(self) -> Dict:
        plan = self.periodization()
        return {"peak_load": max(plan), "avg_load": round(sum(plan)/len(plan), 1) if plan else 0}

def run():
    tp = TrainingPlanner()
    print("Plan:", tp.periodization())
    print("Taper:", tp.taper([100,110,120,130], 2))
    print("ACWR:", tp.acwr(130, 110))
    print(tp.stats())

if __name__ == "__main__":
    run()
