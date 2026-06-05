"""Task Sequencer — precedence, resources, makespan, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class Task:
    id: str
    duration: float
    resources: Set[str]
    predecessors: Set[str] = field(default_factory=set)

class TaskSequencer:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}

    def add_task(self, t: Task):
        self.tasks[t.id] = t

    def earliest_start(self, task_id: str) -> float:
        t = self.tasks.get(task_id)
        if not t:
            return 0.0
        if not t.predecessors:
            return 0.0
        return max(self.earliest_start(p) + self.tasks[p].duration for p in t.predecessors if p in self.tasks)

    def earliest_finish(self, task_id: str) -> float:
        return self.earliest_start(task_id) + self.tasks[task_id].duration

    def makespan(self) -> float:
        if not self.tasks:
            return 0.0
        return max(self.earliest_finish(t) for t in self.tasks)

    def critical_path(self) -> List[str]:
        ms = self.makespan()
        critical = []
        for t in self.tasks.values():
            if abs(self.earliest_finish(t.id) - ms) < 0.001:
                critical.append(t.id)
        return critical

    def resource_conflicts(self) -> List[Tuple[str, str]]:
        conflicts = []
        ids = list(self.tasks.keys())
        for i in range(len(ids)):
            for j in range(i+1, len(ids)):
                t1, t2 = self.tasks[ids[i]], self.tasks[ids[j]]
                if t1.resources & t2.resources:
                    overlap = not (self.earliest_finish(t1.id) <= self.earliest_start(t2.id) or self.earliest_finish(t2.id) <= self.earliest_start(t1.id))
                    if overlap:
                        conflicts.append((t1.id, t2.id))
        return conflicts

    def stats(self) -> Dict:
        return {
            "tasks": len(self.tasks),
            "makespan": round(self.makespan(), 2),
            "critical_path": self.critical_path()
        }

def run():
    ts = TaskSequencer()
    ts.add_task(Task("A", 3, {"r1"}))
    ts.add_task(Task("B", 4, {"r1", "r2"}, {"A"}))
    ts.add_task(Task("C", 2, {"r2"}, {"A"}))
    ts.add_task(Task("D", 5, {"r1"}, {"B", "C"}))
    print(ts.stats())
    print("Conflicts:", ts.resource_conflicts())

if __name__ == "__main__":
    run()
