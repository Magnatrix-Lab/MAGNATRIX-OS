"""Rehearsal Optimizer — schedule, scene priority, cast conflicts, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class RehearsalOptimizer:
    scenes: List[Dict] = field(default_factory=list)
    available_hours: float = 20.0

    def priority_sort(self) -> List[Dict]:
        return sorted(self.scenes, key=lambda s: s.get("priority", 0), reverse=True)

    def hours_per_scene(self) -> List[Dict]:
        total_weight = sum(s.get("priority", 1) for s in self.scenes)
        if total_weight == 0:
            return []
        return [{"name": s["name"], "hours": round(self.available_hours * s.get("priority", 1) / total_weight, 2)} for s in self.scenes]

    def utilization(self) -> float:
        if not self.scenes:
            return 0.0
        return min(1.0, sum(s.get("priority", 1) for s in self.scenes) / (self.available_hours * 2))

    def stats(self) -> Dict:
        return {"schedule": self.hours_per_scene(), "utilization": round(self.utilization(), 3)}

def run():
    ro = RehearsalOptimizer(scenes=[{"name": "Act1", "priority": 5}, {"name": "Act2", "priority": 3}, {"name": "Act3", "priority": 4}], available_hours=24)
    print(ro.stats())

if __name__ == "__main__":
    run()
