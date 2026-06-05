"""Scheduler — task queue, priority, deadlines, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum, auto
import time
import heapq

@dataclass
class Task:
    task_id: str
    priority: int
    deadline: float
    func: Callable
    args: tuple
    kwargs: Dict
    scheduled_at: float

    def __lt__(self, other):
        return self.priority < other.priority if self.priority != other.priority else self.deadline < other.deadline

class Scheduler:
    def __init__(self):
        self.tasks: List[Task] = []
        self.completed: List[str] = []
        self.failed: List[str] = []

    def schedule(self, task_id: str, priority: int, deadline: float, func: Callable, *args, **kwargs):
        task = Task(task_id, priority, deadline, func, args, kwargs, time.time())
        heapq.heappush(self.tasks, task)

    def run(self, max_tasks: int = None):
        count = 0
        while self.tasks:
            if max_tasks and count >= max_tasks:
                break
            task = heapq.heappop(self.tasks)
            if task.deadline < time.time():
                self.failed.append(task.task_id)
                continue
            try:
                task.func(*task.args, **task.kwargs)
                self.completed.append(task.task_id)
            except Exception as e:
                self.failed.append(task.task_id)
            count += 1

    def overdue(self) -> List[Task]:
        now = time.time()
        return [t for t in self.tasks if t.deadline < now]

    def stats(self) -> Dict:
        return {"pending": len(self.tasks), "completed": len(self.completed), "failed": len(self.failed)}

def run():
    scheduler = Scheduler()
    def job(name):
        print(f"Running {name}")
    scheduler.schedule("a", 1, time.time() + 10, job, "task A")
    scheduler.schedule("b", 0, time.time() + 5, job, "task B")
    scheduler.run()
    print(scheduler.stats())

if __name__ == "__main__":
    run()
