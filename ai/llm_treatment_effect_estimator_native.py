"""Treatment Effect Estimator - ATE/ITE estimation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import random

@dataclass
class TreatmentEffectEstimator:
    treated_outcomes: List[float] = field(default_factory=list)
    control_outcomes: List[float] = field(default_factory=list)

    def ate(self) -> float:
        if not self.treated_outcomes or not self.control_outcomes: return 0.0
        return sum(self.treated_outcomes)/len(self.treated_outcomes) - sum(self.control_outcomes)/len(self.control_outcomes)

    def add_treated(self, outcome: float) -> None:
        self.treated_outcomes.append(outcome)

    def add_control(self, outcome: float) -> None:
        self.control_outcomes.append(outcome)

    def stats(self) -> dict:
        return {"treated": len(self.treated_outcomes), "control": len(self.control_outcomes), "ate": round(self.ate(), 4)}

def run():
    tee = TreatmentEffectEstimator()
    for _ in range(10):
        tee.add_treated(random.gauss(10, 1))
        tee.add_control(random.gauss(8, 1))
    print("ATE:", round(tee.ate(), 4))
    print("Stats:", tee.stats())

if __name__ == "__main__": run()
