"""Treatment Planner — dosage, schedule, adherence, outcomes, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class TreatmentPlanner:
    drug: str = ""
    dose_mg: float = 0.0
    frequency: int = 1
    duration_days: int = 7
    half_life: float = 6.0

    def steady_state(self) -> float:
        return self.dose_mg / (1 - math.exp(-0.693 * self.frequency / self.half_life)) if self.frequency > 0 else 0.0

    def trough_level(self) -> float:
        return self.steady_state() * math.exp(-0.693 / self.half_life)

    def schedule(self) -> List[float]:
        levels = []
        concentration = 0.0
        for day in range(self.duration_days):
            for _ in range(self.frequency):
                concentration += self.dose_mg
                concentration *= math.exp(-0.693 / self.half_life)
            levels.append(concentration)
        return levels

    def adherence_effect(self, adherence: float) -> float:
        return adherence ** 2

    def therapeutic_window(self, min_eff: float, max_safe: float) -> bool:
        ss = self.steady_state()
        return min_eff <= ss <= max_safe

    def stats(self) -> Dict:
        return {"steady_state": round(self.steady_state(), 2), "trough": round(self.trough_level(), 2)}

def run():
    tp = TreatmentPlanner(drug="Amoxicillin", dose_mg=500, frequency=3, duration_days=7, half_life=1.5)
    print(tp.stats())
    print("Schedule day 1:", tp.schedule()[0])
    print("In window:", tp.therapeutic_window(1, 50))

if __name__ == "__main__":
    run()
