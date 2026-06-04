"""Workflow Engine - DAG workflow execution for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum, auto
from collections import deque

class TaskStatus(Enum):
    PENDING = auto(); RUNNING = auto(); COMPLETED = auto(); FAILED = auto()

@dataclass
class WorkflowTask:
    task_id: str
    action: callable
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING

@dataclass
class WorkflowEngine:
    tasks: Dict[str, WorkflowTask] = field(default_factory=dict)
    results: Dict[str, any] = field(default_factory=dict)

    def add_task(self, task: WorkflowTask) -> None:
        self.tasks[task.task_id] = task

    def execute(self) -> Dict[str, any]:
        in_degree = {t.task_id: len(t.dependencies) for t in self.tasks.values()}
        queue = deque([t for t in self.tasks.values() if in_degree[t.task_id] == 0])
        while queue:
            task = queue.popleft()
            task.status = TaskStatus.RUNNING
            try:
                self.results[task.task_id] = task.action(self.results)
                task.status = TaskStatus.COMPLETED
            except Exception:
                task.status = TaskStatus.FAILED
                continue
            for other in self.tasks.values():
                if task.task_id in other.dependencies:
                    in_degree[other.task_id] -= 1
                    if in_degree[other.task_id] == 0:
                        queue.append(other)
        return self.results

    def stats(self) -> dict:
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
        return {"tasks": len(self.tasks), "completed": completed, "failed": failed}

def run():
    we = WorkflowEngine()
    we.add_task(WorkflowTask("t1", lambda ctx: 10, []))
    we.add_task(WorkflowTask("t2", lambda ctx: ctx["t1"] * 2, ["t1"]))
    we.execute()
    print("Results:", we.results)
    print("Stats:", we.stats())

if __name__ == "__main__": run()
