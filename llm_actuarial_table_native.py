"""Actuarial Table — life expectancy, mortality rates, qx, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ActuarialTable:
    ages: List[int] = field(default_factory=list)
    qx: List[float] = field(default_factory=list)
    """probability of death at age x"""

    def life_expectancy(self, age: int) -> float:
        if age not in self.ages:
            return 0.0
        idx = self.ages.index(age)
        remaining = 0.0
        lx = 1.0
        for i in range(idx, len(self.ages)):
            remaining += lx
            lx *= (1 - self.qx[i])
        return remaining

    def survival_probability(self, from_age: int, to_age: int) -> float:
        if from_age not in self.ages or to_age not in self.ages:
            return 0.0
        f_idx = self.ages.index(from_age)
        t_idx = self.ages.index(to_age)
        p = 1.0
        for i in range(f_idx, t_idx):
            p *= (1 - self.qx[i])
        return p

    def force_of_mortality(self, age: int) -> float:
        if age not in self.ages:
            return 0.0
        idx = self.ages.index(age)
        return -math.log(1 - self.qx[idx]) if self.qx[idx] < 1 else 0.0

    def stats(self, age: int) -> Dict:
        return {"age": age, "qx": self.qx[self.ages.index(age)] if age in self.ages else 0, "le": round(self.life_expectancy(age), 2)}

def run():
    at = ActuarialTable(ages=[20,30,40,50,60,70,80], qx=[0.001,0.002,0.005,0.01,0.02,0.05,0.1])
    print(at.stats(30))
    print("Survival 30->60:", at.survival_probability(30, 60))

if __name__ == "__main__":
    run()
