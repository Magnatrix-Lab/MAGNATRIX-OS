"""Mission Planner — objectives, constraints, resources, timeline, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

@dataclass
class MissionObjective:
    id: str
    priority: int
    duration: float
    resources: List[str]
    prerequisites: List[str] = field(default_factory=list)

class MissionPlanner:
    def __init__(self):
        self.objectives: List[MissionObjective] = []
        self.resources: Set[str] = set()

    def add_objective(self, o: MissionObjective):
        self.objectives.append(o)
        self.resources.update(o.resources)

    def feasible_order(self) -> List[str]:
        done = set()
        order = []
        remaining = list(self.objectives)
        while remaining:
            found = False
            for o in remaining:
                if all(p in done for p in o.prerequisites):
                    order.append(o.id)
                    done.add(o.id)
                    remaining.remove(o)
                    found = True
                    break
            if not found:
                break
        return order

    def resource_conflict(self) -> List[Tuple[str, str]]:
        conflicts = []
        for i, o1 in enumerate(self.objectives):
            for o2 in self.objectives[i+1:]:
                shared = set(o1.resources) & set(o2.resources)
                if shared and not (o1.id in o2.prerequisites or o2.id in o1.prerequisites):
                    conflicts.append((o1.id, o2.id))
        return conflicts

    def total_duration(self) -> float:
        order = self.feasible_order()
        durations = {o.id: o.duration for o in self.objectives}
        end_times = {}
        for oid in order:
            o = next((x for x in self.objectives if x.id == oid), None)
            pred_end = max((end_times[p] for p in o.prerequisites if p in end_times), default=0) if o else 0
            end_times[oid] = pred_end + durations.get(oid, 0)
        return max(end_times.values()) if end_times else 0

    def stats(self) -> Dict:
        return {"objectives": len(self.objectives), "resources": len(self.resources), "duration": self.total_duration()}

def run():
    mp = MissionPlanner()
    mp.add_objective(MissionObjective("Intel", 1, 2, ["team_a"]))
    mp.add_objective(MissionObjective("Infil", 2, 4, ["team_a"], ["Intel"]))
    mp.add_objective(MissionObjective("Exfil", 3, 2, ["team_a"], ["Infil"]))
    print("Order:", mp.feasible_order())
    print("Conflicts:", mp.resource_conflict())
    print(mp.stats())

if __name__ == "__main__":
    run()
