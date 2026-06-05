"""Native stdlib module: Throughput Calculator
Calculates production throughput, bottleneck rates, and takt time.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class ProcessStep:
    name: str
    cycle_time_sec: float
    num_machines: int = 1

@dataclass
class ThroughputCalculator:
    line_name: str
    available_time_sec: float
    demand_units: int
    steps: List[ProcessStep] = field(default_factory=list)

    def takt_time_sec(self) -> float:
        if self.demand_units == 0:
            return 0.0
        return self.available_time_sec / self.demand_units

    def bottleneck_time(self) -> float:
        if not self.steps:
            return 0.0
        return max(s.cycle_time_sec / s.num_machines for s in self.steps)

    def bottleneck_name(self) -> str:
        if not self.steps:
            return ""
        bottleneck = max(self.steps, key=lambda s: s.cycle_time_sec / s.num_machines)
        return bottleneck.name

    def max_throughput(self) -> float:
        bottleneck = self.bottleneck_time()
        if bottleneck == 0:
            return 0.0
        return self.available_time_sec / bottleneck

    def meets_demand(self) -> bool:
        return self.max_throughput() >= self.demand_units

    def stats(self) -> Dict:
        return {
            "line": self.line_name,
            "takt_time_sec": round(self.takt_time_sec(), 2),
            "bottleneck": self.bottleneck_name(),
            "bottleneck_time_sec": round(self.bottleneck_time(), 2),
            "max_throughput": int(self.max_throughput()),
            "meets_demand": self.meets_demand(),
        }

def run():
    tc = ThroughputCalculator(
        line_name="Widget Line",
        available_time_sec=28800,
        demand_units=800,
        steps=[
            ProcessStep("cut", 30, 2),
            ProcessStep("drill", 45, 1),
            ProcessStep("assemble", 25, 2),
            ProcessStep("paint", 40, 2),
            ProcessStep("inspect", 20, 1),
        ]
    )
    print(tc.stats())

if __name__ == "__main__":
    run()
