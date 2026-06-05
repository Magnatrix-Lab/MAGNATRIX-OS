"""Epidemiology Tracker — R0, doubling time, SIR model, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class EpidemiologyTracker:
    population: float = 1000000.0
    infected: float = 100.0
    recovered: float = 0.0
    beta: float = 0.3
    gamma: float = 0.1

    def susceptible(self) -> float:
        return self.population - self.infected - self.recovered

    def r0(self) -> float:
        return self.beta / self.gamma if self.gamma > 0 else 0.0

    def doubling_time(self) -> float:
        r = self.r0()
        if r <= 1:
            return float('inf')
        return math.log(2) / (self.beta * (self.susceptible() / self.population) - self.gamma)

    def sir_step(self, dt: float = 1.0):
        s = self.susceptible()
        new_infections = self.beta * s * self.infected / self.population * dt
        new_recoveries = self.gamma * self.infected * dt
        self.infected += new_infections - new_recoveries
        self.recovered += new_recoveries

    def simulate(self, days: int) -> List[Tuple[float, float, float]]:
        results = []
        for _ in range(days):
            self.sir_step()
            results.append((self.susceptible(), self.infected, self.recovered))
        return results

    def herd_immunity_threshold(self) -> float:
        r = self.r0()
        return 1 - 1/r if r > 0 else 0.0

    def stats(self) -> Dict:
        return {"R0": round(self.r0(), 2), "doubling": round(self.doubling_time(), 1), "herd": round(self.herd_immunity_threshold(), 3)}

def run():
    et = EpidemiologyTracker()
    print(et.stats())
    sim = et.simulate(30)
    print("Day 30:", sim[-1])

if __name__ == "__main__":
    run()
