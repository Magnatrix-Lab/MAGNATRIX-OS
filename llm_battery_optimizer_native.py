"""Battery Optimizer — SOC, charge/discharge, cycle life, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class BatteryOptimizer:
    capacity: float = 100.0
    soc: float = 50.0
    charge_rate_max: float = 50.0
    discharge_rate_max: float = 50.0
    efficiency: float = 0.95
    cycles: int = 0
    cycle_depths: List[float] = field(default_factory=list)

    def charge(self, power: float, dt: float) -> float:
        power = min(power, self.charge_rate_max)
        energy = power * dt * self.efficiency
        available = self.capacity - self.soc
        added = min(energy, available)
        self.soc += added
        return added

    def discharge(self, power: float, dt: float) -> float:
        power = min(power, self.discharge_rate_max)
        energy = power * dt * self.efficiency
        removed = min(energy, self.soc)
        self.soc -= removed
        return removed

    def schedule(self, prices: List[float], loads: List[float]) -> List[float]:
        actions = []
        for price, load in zip(prices, loads):
            if price < 0.1 and self.soc < self.capacity * 0.9:
                actions.append(self.charge_rate_max)
            elif price > 0.3 and self.soc > self.capacity * 0.2:
                actions.append(-min(load, self.discharge_rate_max))
            else:
                actions.append(0)
        return actions

    def cycle_count(self, depth_threshold: float = 5.0) -> int:
        return sum(1 for d in self.cycle_depths if d >= depth_threshold)

    def stats(self) -> Dict:
        return {"capacity": self.capacity, "soc": round(self.soc, 2), "soc_pct": round(self.soc/self.capacity*100, 1), "cycles": self.cycles}

def run():
    bat = BatteryOptimizer()
    bat.charge(30, 1)
    bat.discharge(20, 1)
    print(bat.stats())

if __name__ == "__main__":
    run()
