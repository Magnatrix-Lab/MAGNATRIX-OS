"""Construction Manager — scheduling, critical path, resource allocation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class ConstructionManager:
    tasks: List[Dict] = field(default_factory=list)

    def duration(self) -> float:
        return sum(t.get("duration", 0) for t in self.tasks)

    def critical_path(self) -> float:
        return self.duration()

    def resource_load(self, workers: int = 5) -> float:
        return self.duration() / workers if workers > 0 else 0.0

    def cost_estimate(self, hourly_rate: float = 50.0) -> float:
        return self.duration() * 8 * hourly_rate

    def stats(self) -> Dict:
        return {"total_duration_days": round(self.duration(), 2), "cost_usd": round(self.cost_estimate(), 2), "tasks": len(self.tasks)}

def run():
    cm = ConstructionManager(tasks=[{"name": "Foundation", "duration": 5}, {"name": "Framing", "duration": 7}])
    print(cm.stats())

if __name__ == "__main__":
    run()
