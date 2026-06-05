"""Ecosystem Modeler — predator-prey, carrying capacity, succession, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class EcosystemModeler:
    prey: float = 100.0
    predators: float = 20.0
    prey_growth: float = 1.0
    predation_rate: float = 0.02
    predator_efficiency: float = 0.01
    predator_death: float = 0.5

    def lotka_volterra_step(self, dt: float = 0.1):
        dprey = (self.prey_growth * self.prey - self.predation_rate * self.prey * self.predators) * dt
        dpred = (self.predator_efficiency * self.prey * self.predators - self.predator_death * self.predators) * dt
        self.prey = max(0, self.prey + dprey)
        self.predators = max(0, self.predators + dpred)

    def simulate(self, steps: int = 100) -> List[Tuple[float, float]]:
        results = [(self.prey, self.predators)]
        for _ in range(steps):
            self.lotka_volterra_step()
            results.append((self.prey, self.predators))
        return results

    def carrying_capacity(self, env_capacity: float = 500.0) -> float:
        return env_capacity

    def equilibrium_prey(self) -> float:
        return self.predator_death / self.predator_efficiency if self.predator_efficiency > 0 else 0.0

    def equilibrium_predators(self) -> float:
        return self.prey_growth / self.predation_rate if self.predation_rate > 0 else 0.0

    def stats(self) -> Dict:
        return {"prey": round(self.prey, 1), "predators": round(self.predators, 1), "eq_prey": round(self.equilibrium_prey(), 1), "eq_pred": round(self.equilibrium_predators(), 1)}

def run():
    em = EcosystemModeler(prey=200, predators=30)
    sim = em.simulate(50)
    print(em.stats())
    print("Final:", sim[-1])

if __name__ == "__main__":
    run()
