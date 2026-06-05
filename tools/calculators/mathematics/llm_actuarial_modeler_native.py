"""Actuarial Modeler — present value, annuity, commutation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ActuarialModeler:
    interest_rate: float = 0.05
    mortality_table: List[float] = field(default_factory=list)

    def v(self) -> float:
        return 1 / (1 + self.interest_rate)

    def annuity_certain(self, n: int) -> float:
        v = self.v()
        return (1 - v**n) / self.interest_rate if self.interest_rate > 0 else n

    def annuity_life(self, age: int) -> float:
        if not self.mortality_table or age >= len(self.mortality_table):
            return 0.0
        v = self.v()
        total = 0.0
        px = 1.0
        for t in range(min(100, len(self.mortality_table) - age)):
            px *= (1 - self.mortality_table[age + t])
            total += v**t * px
        return total

    def insurance_life(self, age: int) -> float:
        if not self.mortality_table or age >= len(self.mortality_table):
            return 0.0
        v = self.v()
        total = 0.0
        px = 1.0
        for t in range(min(100, len(self.mortality_table) - age)):
            q = self.mortality_table[age + t]
            total += v**(t+1) * px * q
            px *= (1 - q)
        return total

    def net_single_premium(self, age: int, benefit: float) -> float:
        return benefit * self.insurance_life(age)

    def stats(self, age: int) -> Dict:
        return {"annuity_certain_10": round(self.annuity_certain(10), 4), "annuity_life": round(self.annuity_life(age), 4), "insurance_life": round(self.insurance_life(age), 4)}

def run():
    qx = [0.001] * 5 + [0.002] * 10 + [0.005] * 20 + [0.01] * 30 + [0.03] * 30
    am = ActuarialModeler(interest_rate=0.05, mortality_table=qx)
    print(am.stats(30))
    print("NSP 100k:", am.net_single_premium(30, 100000))

if __name__ == "__main__":
    run()
