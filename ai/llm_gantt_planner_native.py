"""Gantt Planner - Timeline visualization planner for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto

@dataclass
class GanttPlanner:
    tasks: List[Dict] = field(default_factory=list)

    def add_task(self, task_id: str, start: float, duration: float, resource: str = "") -> None:
        self.tasks.append({"id": task_id, "start": start, "duration": duration, "resource": resource, "end": start + duration})

    def check_conflicts(self) -> List[Tuple[str, str]]:
        conflicts = []
        for i, t1 in enumerate(self.tasks):
            for t2 in self.tasks[i+1:]:
                if t1["resource"] == t2["resource"] and t1["start"] < t2["end"] and t2["start"] < t1["end"]:
                    conflicts.append((t1["id"], t2["id"]))
        return conflicts

    def critical_path(self) -> List[str]:
        if not self.tasks: return []
        ends = {t["id"]: t["end"] for t in self.tasks}
        return sorted(ends.keys(), key=lambda k: ends[k], reverse=True)[:3]

    def stats(self) -> dict:
        return {"tasks": len(self.tasks), "conflicts": len(self.check_conflicts()), "makespan": round(max(t["end"] for t in self.tasks), 2) if self.tasks else 0}

def run():
    gp = GanttPlanner()
    gp.add_task("A", 0, 3, "CPU")
    gp.add_task("B", 1, 4, "CPU")
    gp.add_task("C", 5, 2, "CPU")
    print("Conflicts:", gp.check_conflicts())
    print("Stats:", gp.stats())

if __name__ == "__main__": run()
