"""Construction Scheduler — CPM, critical path, float, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class Task:
    id: str
    duration: float
    predecessors: List[str] = field(default_factory=list)
    es: float = 0.0
    ef: float = 0.0
    ls: float = 0.0
    lf: float = 0.0

class ConstructionScheduler:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}

    def add_task(self, t: Task):
        self.tasks[t.id] = t

    def forward_pass(self):
        for t in self.tasks.values():
            t.es = 0.0
        changed = True
        while changed:
            changed = False
            for t in self.tasks.values():
                pred_ef = max((self.tasks[p].ef for p in t.predecessors if p in self.tasks), default=0)
                if t.es != pred_ef:
                    t.es = pred_ef
                    t.ef = t.es + t.duration
                    changed = True

    def backward_pass(self):
        max_ef = max(t.ef for t in self.tasks.values()) if self.tasks else 0
        for t in self.tasks.values():
            t.lf = max_ef
            t.ls = max_ef - t.duration
        changed = True
        while changed:
            changed = False
            for t in self.tasks.values():
                successors = [s for s in self.tasks.values() if t.id in s.predecessors]
                min_ls = min((s.ls for s in successors), default=t.lf)
                if t.lf != min_ls:
                    t.lf = min_ls
                    t.ls = t.lf - t.duration
                    changed = True

    def critical_path(self) -> List[str]:
        self.forward_pass()
        self.backward_pass()
        return [t.id for t in self.tasks.values() if abs(t.es - t.ls) < 0.001]

    def total_float(self, task_id: str) -> float:
        t = self.tasks.get(task_id)
        return (t.ls - t.es) if t else 0.0

    def project_duration(self) -> float:
        self.forward_pass()
        return max(t.ef for t in self.tasks.values()) if self.tasks else 0

    def stats(self) -> Dict:
        return {"duration": self.project_duration(), "critical_tasks": len(self.critical_path())}

def run():
    cs = ConstructionScheduler()
    cs.add_task(Task("A", 3))
    cs.add_task(Task("B", 4, ["A"]))
    cs.add_task(Task("C", 2, ["A"]))
    cs.add_task(Task("D", 5, ["B", "C"]))
    print("Critical path:", cs.critical_path())
    print(cs.stats())

if __name__ == "__main__":
    run()
