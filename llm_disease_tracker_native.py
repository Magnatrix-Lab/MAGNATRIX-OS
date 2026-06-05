"""Disease Tracker — outbreak, R0, vaccination, quarantine, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class DiseaseTracker:
    population: int = 1000
    susceptible: int = 990
    infected: int = 10
    recovered: int = 0
    beta: float = 0.3
    gamma: float = 0.1
    vaccination_rate: float = 0.0

    def r0(self) -> float:
        return self.beta / self.gamma if self.gamma > 0 else 0.0

    def herd_immunity_threshold(self) -> float:
        r = self.r0()
        return 1 - 1/r if r > 1 else 0.0

    def vaccinate(self, rate: float):
        self.vaccination_rate = rate
        vaccinated = int(self.susceptible * rate)
        self.susceptible -= vaccinated
        self.recovered += vaccinated

    def step(self, dt: float = 1.0):
        new_infected = min(self.susceptible, int(self.beta * self.susceptible * self.infected / self.population * dt))
        new_recovered = min(self.infected, int(self.gamma * self.infected * dt))
        self.susceptible -= new_infected
        self.infected += new_infected - new_recovered
        self.recovered += new_recovered

    def simulate(self, days: int = 30) -> List[Tuple[int, int, int]]:
        results = [(self.susceptible, self.infected, self.recovered)]
        for _ in range(days):
            self.step()
            results.append((self.susceptible, self.infected, self.recovered))
        return results

    def outbreak_risk(self) -> str:
        if self.r0() > 2.5: return "high"
        elif self.r0() > 1.5: return "moderate"
        return "low"

    def quarantine_needed(self, threshold: int = 50) -> bool:
        return self.infected > threshold

    def stats(self) -> Dict:
        return {"r0": round(self.r0(), 2), "herd_threshold": round(self.herd_immunity_threshold(), 2), "risk": self.outbreak_risk(), "quarantine": self.quarantine_needed()}

def run():
    dt = DiseaseTracker()
    print(dt.stats())
    dt.vaccinate(0.6)
    sim = dt.simulate(20)
    print("Day 20:", sim[-1])

if __name__ == "__main__":
    run()
