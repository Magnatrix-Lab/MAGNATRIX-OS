"""Ecosystem Modeler — Lotka-Volterra, predator-prey, carrying capacity, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class EcosystemModeler:
    prey: float = 100.0
    predators: float = 10.0
    prey_growth: float = 0.1
    predation_rate: float = 0.01
    predator_efficiency: float = 0.005
    predator_death: float = 0.05

    def lotka_volterra_step(self, dt: float = 1.0) -> Tuple[float, float]:
        dprey = self.prey_growth * self.prey - self.predation_rate * self.prey * self.predators
        dpred = self.predator_efficiency * self.prey * self.predators - self.predator_death * self.predators
        self.prey = max(0, self.prey + dprey * dt)
        self.predators = max(0, self.predators + dpred * dt)
        return self.prey, self.predators

    def simulate(self, steps: int = 100) -> List[Tuple[float, float]]:
        results = []
        for _ in range(steps):
            self.lotka_volterra_step()
            results.append((self.prey, self.predators))
        return results

    def equilibrium(self) -> Tuple[float, float]:
        if self.predation_rate == 0 or self.predator_efficiency == 0:
            return 0, 0
        prey_eq = self.predator_death / self.predator_efficiency
        pred_eq = self.prey_growth / self.predation_rate
        return prey_eq, pred_eq

    def stats(self) -> Dict:
        return {"prey": round(self.prey, 1), "predators": round(self.predators, 1), "equilibrium": self.equilibrium()}

def run():
    em = EcosystemModeler()
    print(em.stats())
    sim = em.simulate(50)
    print("After 50 steps:", sim[-1])

if __name__ == "__main__":
    run()
