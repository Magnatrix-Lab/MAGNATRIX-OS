"""LLM Task Scheduler — Native Python (stdlib only)."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5

class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

@dataclass
class ScheduledTask:
    id: str
    task: Callable[[], Any]
    priority: TaskPriority = TaskPriority.NORMAL
    scheduled_at: float = 0.0
    delay: float = 0.0
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None

class TaskScheduler:
    def __init__(self) -> None:
        self._tasks: List[ScheduledTask] = []

    def schedule(self, task: ScheduledTask) -> None:
        task.scheduled_at = time.time() + task.delay
        self._tasks.append(task)

    def run_all(self) -> Dict[str, Any]:
        self._tasks.sort(key=lambda t: (t.priority.value, t.scheduled_at))
        results = {}
        for task in self._tasks:
            if task.status == TaskStatus.PENDING and time.time() >= task.scheduled_at:
                task.status = TaskStatus.RUNNING
                try:
                    task.result = task.task()
                    task.status = TaskStatus.COMPLETED
                except Exception as ex:
                    task.status = TaskStatus.FAILED
                    task.error = str(ex)
                results[task.id] = task.result
        return results

    def cancel(self, task_id: str) -> bool:
        for task in self._tasks:
            if task.id == task_id and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {"total": len(self._tasks), "completed": sum(1 for t in self._tasks if t.status == TaskStatus.COMPLETED), "failed": sum(1 for t in self._tasks if t.status == TaskStatus.FAILED), "pending": sum(1 for t in self._tasks if t.status == TaskStatus.PENDING)}

def run() -> None:
    print("Task Scheduler test")
    e = TaskScheduler()
    e.schedule(ScheduledTask("t1", lambda: "Result A", TaskPriority.HIGH, delay=0.0))
    e.schedule(ScheduledTask("t2", lambda: "Result B", TaskPriority.NORMAL, delay=0.0))
    e.schedule(ScheduledTask("t3", lambda: "Result C", TaskPriority.CRITICAL, delay=0.0))
    results = e.run_all()
    print("  Results: " + str(results))
    print("  Stats: " + str(e.get_stats()))
    print("Task Scheduler test complete.")

if __name__ == "__main__":
    run()
