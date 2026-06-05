"""Parasite Lifecycle — stages, hosts, prepatent, transmission, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ParasiteLifecycle:
    stages: List[str] = field(default_factory=list)
    prepatent_period_days: int = 14
    lifespan_days: int = 30
    r0: float = 2.0

    def generation_time(self) -> float:
        return self.prepatent_period_days + self.lifespan_days / 2

    def daily_reproduction(self) -> float:
        if self.lifespan_days <= 0:
            return 0.0
        return self.r0 / self.lifespan_days

    def doubling_time(self) -> float:
        if self.daily_reproduction() <= 0:
            return float('inf')
        return 0.693 / self.daily_reproduction()

    def transmission_probability(self, contacts_per_day: float, infectivity: float) -> float:
        return 1 - (1 - infectivity) ** contacts_per_day

    def stats(self) -> Dict:
        return {"stages": len(self.stages), "generation_time": self.generation_time(), "r0": self.r0, "doubling": round(self.doubling_time(), 1)}

def run():
    pl = ParasiteLifecycle(["egg", "larva", "adult"], 10, 20, 3.5)
    print(pl.stats())
    print("Transmission:", pl.transmission_probability(5, 0.2))

if __name__ == "__main__":
    run()
