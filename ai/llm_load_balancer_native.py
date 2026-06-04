"""Load Balancer - Traffic distribution for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import random

class LBStrategy(Enum):
    ROUND_ROBIN = auto(); LEAST_CONNECTIONS = auto(); RANDOM = auto()

@dataclass
class LoadBalancer:
    strategy: LBStrategy = LBStrategy.ROUND_ROBIN
    backends: List[Dict] = field(default_factory=list)
    current_index: int = 0

    def add_backend(self, backend_id: str, weight: int = 1) -> None:
        self.backends.append({"id": backend_id, "weight": weight, "connections": 0, "healthy": True})

    def get_backend(self) -> Optional[str]:
        healthy = [b for b in self.backends if b["healthy"]]
        if not healthy: return None
        if self.strategy == LBStrategy.ROUND_ROBIN:
            result = healthy[self.current_index % len(healthy)]
            self.current_index += 1
            return result["id"]
        elif self.strategy == LBStrategy.LEAST_CONNECTIONS:
            return min(healthy, key=lambda b: b["connections"])["id"]
        elif self.strategy == LBStrategy.RANDOM:
            return random.choice(healthy)["id"]
        return None

    def mark_healthy(self, backend_id: str, healthy: bool) -> None:
        for b in self.backends:
            if b["id"] == backend_id: b["healthy"] = healthy

    def stats(self) -> dict:
        return {"strategy": self.strategy.name, "backends": len(self.backends), "healthy": sum(1 for b in self.backends if b["healthy"])}

def run():
    lb = LoadBalancer(LBStrategy.ROUND_ROBIN)
    lb.add_backend("be1", 2); lb.add_backend("be2", 1); lb.add_backend("be3", 1)
    for _ in range(5): print("Backend:", lb.get_backend())
    print("Stats:", lb.stats())

if __name__ == "__main__": run()
