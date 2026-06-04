"""Task Scheduler - Priority-based scheduling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import heapq

class SchedulingPolicy(Enum):
    FIFO = auto(); SJF = auto(); PRIORITY = auto(); EDF = auto()

@dataclass
class Task:
    task_id: str
    duration: float
    priority: int = 0
    deadline: float = float('inf')
    dependencies: List[str] = field(default_factory=list)

@dataclass
class TaskScheduler:
    policy: SchedulingPolicy = SchedulingPolicy.PRIORITY
    tasks: Dict[str, Task] = field(default_factory=dict)
    completed: List[str] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task

    def schedule(self) -> List[str]:
        available = [t for t in self.tasks.values() if not t.dependencies or all(d in self.completed for d in t.dependencies)]
        if self.policy == SchedulingPolicy.SJF:
            available.sort(key=lambda t: t.duration)
        elif self.policy == SchedulingPolicy.PRIORITY:
            available.sort(key=lambda t: -t.priority)
        elif self.policy == SchedulingPolicy.EDF:
            available.sort(key=lambda t: t.deadline)
        return [t.task_id for t in available]

    def complete(self, task_id: str) -> None:
        if task_id in self.tasks and task_id not in self.completed:
            self.completed.append(task_id)

    def stats(self) -> dict:
        return {"tasks": len(self.tasks), "completed": len(self.completed), "policy": self.policy.name}

def run():
    ts = TaskScheduler(SchedulingPolicy.PRIORITY)
    ts.add_task(Task("t1", 3, 2, dependencies=[]))
    ts.add_task(Task("t2", 2, 1, dependencies=["t1"]))
    ts.add_task(Task("t3", 1, 3, dependencies=[]))
    print("Schedule:", ts.schedule())
    ts.complete("t1")
    print("After t1:", ts.schedule())
    print("Stats:", ts.stats())

if __name__ == "__main__": run()
