"""Mortality Table — life expectancy, qx, survivors, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class MortalityTable:
    qx: List[float] = field(default_factory=list)
    """Probability of death at each age"""

    def survivors(self, l0: int = 100000) -> List[int]:
        lx = [l0]
        for q in self.qx:
            lx.append(int(lx[-1] * (1 - q)))
        return lx

    def life_expectancy(self, age: int) -> float:
        if age >= len(self.qx):
            return 0.0
        lx = self.survivors()
        ex = sum(lx[i] for i in range(age, min(len(lx), len(self.qx) + 1))) / lx[age] if lx[age] > 0 else 0
        return ex - 0.5

    def probability_survive(self, from_age: int, to_age: int) -> float:
        lx = self.survivors()
        if from_age >= len(lx) or to_age >= len(lx):
            return 0.0
        return lx[to_age] / lx[from_age] if lx[from_age] > 0 else 0.0

    def death_benefit_expected(self, age: int, benefit: float) -> float:
        if age >= len(self.qx):
            return 0.0
        return self.qx[age] * benefit

    def stats(self, age: int) -> Dict:
        return {"qx": self.qx[age] if age < len(self.qx) else 0, "life_exp": round(self.life_expectancy(age), 1)}

def run():
    qx = [0.001, 0.001, 0.001, 0.001, 0.001] + [0.002] * 10 + [0.005] * 20 + [0.01] * 30 + [0.03] * 30
    mt = MortalityTable(qx)
    print(mt.stats(30))
    print("Survive 30->60:", mt.probability_survive(30, 60))

if __name__ == "__main__":
    run()
