"""Energy Load Balancer — demand response, peak shaving, dispatch, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class LoadBalancerEnergy:
    loads: List[float] = field(default_factory=list)
    capacity: float = 1000.0
    peak_threshold: float = 0.8

    def current_load(self) -> float:
        return sum(self.loads)

    def utilization(self) -> float:
        return self.current_load() / self.capacity if self.capacity > 0 else 0.0

    def peak_shave(self, flexible: List[float]) -> Tuple[List[float], float]:
        peak = self.capacity * self.peak_threshold
        excess = max(0, self.current_load() - peak)
        shaved = []
        for f in flexible:
            reduce = min(f, excess)
            shaved.append(f - reduce)
            excess -= reduce
        return shaved, excess

    def dispatch_priority(self, generators: List[Tuple[str, float, float]]) -> List[str]:
        """name, cost, capacity"""
        sorted_gen = sorted(generators, key=lambda g: g[1])
        dispatched = []
        remaining = self.current_load()
        for name, cost, cap in sorted_gen:
            if remaining <= 0:
                break
            dispatched.append(name)
            remaining -= cap
        return dispatched

    def stats(self) -> Dict:
        return {"total_load": self.current_load(), "utilization": round(self.utilization(), 3), "capacity": self.capacity}

def run():
    lb = LoadBalancerEnergy([200,300,400], capacity=1000, peak_threshold=0.7)
    print(lb.stats())
    print("Dispatch:", lb.dispatch_priority([("A",0.1,300),("B",0.05,500),("C",0.2,400)]))

if __name__ == "__main__":
    run()
