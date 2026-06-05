"""Native stdlib module: Grid Load Calculator
Calculates electrical load diversity, peak demand, and load factor.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Load:
    name: str
    rated_kw: float
    quantity: int = 1
    duty_factor: float = 1.0
    diversity_factor: float = 1.0

@dataclass
class GridLoadCalculator:
    site_name: str
    loads: List[Load] = field(default_factory=list)
    peak_hours: int = 1

    def connected_load(self) -> float:
        return sum(l.rated_kw * l.quantity for l in self.loads)

    def diversified_load(self) -> float:
        return sum(l.rated_kw * l.quantity * l.duty_factor * l.diversity_factor for l in self.loads)

    def peak_demand(self) -> float:
        return max(self.diversified_load(), self.connected_load() * 0.7)

    def load_factor(self, energy_kwh: float) -> float:
        if self.peak_demand() == 0 or self.peak_hours == 0:
            return 0.0
        return energy_kwh / (self.peak_demand() * self.peak_hours)

    def stats(self, monthly_energy_kwh: float = 0) -> Dict:
        return {
            "site": self.site_name,
            "connected_load_kw": round(self.connected_load(), 2),
            "diversified_load_kw": round(self.diversified_load(), 2),
            "peak_demand_kw": round(self.peak_demand(), 2),
            "load_factor": round(self.load_factor(monthly_energy_kwh), 3) if monthly_energy_kwh else None,
        }

def run():
    gl = GridLoadCalculator(
        site_name="Factory A",
        loads=[
            Load("motors", 50, 4, 0.8, 0.9),
            Load("lighting", 20, 1, 1.0, 0.85),
            Load("hvac", 30, 2, 0.7, 0.95),
            Load("office", 15, 1, 0.6, 0.8),
        ]
    )
    print(gl.stats(monthly_energy_kwh=45000))

if __name__ == "__main__":
    run()
