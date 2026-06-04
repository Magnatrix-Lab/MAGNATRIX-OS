"""Auto Scaler - Horizontal scaling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum, auto

class ScaleDirection(Enum):
    UP = auto(); DOWN = auto(); NONE = auto()

@dataclass
class AutoScaler:
    min_instances: int = 1; max_instances: int = 10
    target_cpu: float = 70.0; cooldown: int = 60
    current_instances: int = 1
    metrics_history: List[Dict] = field(default_factory=list)

    def evaluate(self, cpu_utilization: float, requests_per_second: float) -> ScaleDirection:
        if cpu_utilization > self.target_cpu * 1.2 and self.current_instances < self.max_instances:
            return ScaleDirection.UP
        if cpu_utilization < self.target_cpu * 0.5 and self.current_instances > self.min_instances:
            return ScaleDirection.DOWN
        return ScaleDirection.NONE

    def scale(self, cpu_utilization: float, requests_per_second: float) -> int:
        direction = self.evaluate(cpu_utilization, requests_per_second)
        if direction == ScaleDirection.UP:
            self.current_instances = min(self.max_instances, self.current_instances + 1)
        elif direction == ScaleDirection.DOWN:
            self.current_instances = max(self.min_instances, self.current_instances - 1)
        return self.current_instances

    def stats(self) -> dict:
        return {"current": self.current_instances, "min": self.min_instances, "max": self.max_instances}

def run():
    as_ = AutoScaler(1, 5, 70.0)
    for cpu in [30, 50, 85, 90, 95, 40, 20]:
        new_count = as_.scale(cpu, 100)
        print(f"CPU {cpu}% -> instances: {new_count}")
    print("Stats:", as_.stats())

if __name__ == "__main__": run()
