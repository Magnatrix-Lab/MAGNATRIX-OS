"""Disaster Recovery — timeline, resources, phases, dependencies, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class RecoveryPhase:
    name: str
    duration_days: float
    resources_needed: Dict[str, int]
    dependencies: List[str] = field(default_factory=list)
    completed: bool = False

class DisasterRecovery:
    def __init__(self):
        self.phases: List[RecoveryPhase] = []

    def add_phase(self, p: RecoveryPhase):
        self.phases.append(p)

    def critical_path(self) -> List[str]:
        path = []
        for p in self.phases:
            if not p.dependencies:
                path.append(p.name)
        for p in self.phases:
            if p.dependencies and all(d in path for d in p.dependencies):
                path.append(p.name)
        return path

    def total_duration(self) -> float:
        return sum(p.duration_days for p in self.phases)

    def resource_peak(self) -> Dict[str, int]:
        peak = {}
        for p in self.phases:
            for r, n in p.resources_needed.items():
                peak[r] = max(peak.get(r, 0), n)
        return peak

    def progress(self) -> float:
        if not self.phases:
            return 0.0
        completed = sum(1 for p in self.phases if p.completed)
        return completed / len(self.phases)

    def next_phase(self) -> Optional[str]:
        for p in self.phases:
            if not p.completed and all(d in [x.name for x in self.phases if x.completed] for d in p.dependencies):
                return p.name
        return None

    def stats(self) -> Dict:
        return {"phases": len(self.phases), "duration": self.total_duration(), "progress": self.progress(), "next": self.next_phase()}

def run():
    dr = DisasterRecovery()
    dr.add_phase(RecoveryPhase("Search & Rescue", 3, {"teams": 10, "equipment": 50}))
    dr.add_phase(RecoveryPhase("Infrastructure", 30, {"workers": 100, "materials": 1000}, ["Search & Rescue"]))
    dr.add_phase(RecoveryPhase("Housing", 90, {"builders": 50, "supplies": 500}, ["Infrastructure"]))
    print(dr.stats())
    print("Critical path:", dr.critical_path())
    print("Resource peak:", dr.resource_peak())

if __name__ == "__main__":
    run()
