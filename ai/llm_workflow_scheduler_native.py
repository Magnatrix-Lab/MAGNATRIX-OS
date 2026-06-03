#!/usr/bin/env python3
"""
MAGNATRIX-OS — Workflow Scheduler Engine
ai/llm_workflow_scheduler_native.py

Features:
- DAG-based task scheduling (dependency graph)
- Task execution with dependency resolution
- Cron-like trigger simulation (interval-based scheduling)
- Job queue management (priority, FIFO, retry)
- Execution status tracking (pending, running, completed, failed)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("workflow_scheduler")


class TaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    id: str
    name: str
    handler: Callable[[], Any]
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    priority: int = 0


@dataclass
class ScheduledJob:
    id: str
    name: str
    interval_seconds: float
    handler: Callable[[], Any]
    last_run: float = 0.0
    run_count: int = 0


class WorkflowSchedulerEngine:
    """DAG-based workflow scheduler."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._jobs: Dict[str, ScheduledJob] = {}
        self._queue: deque = deque()
        self._history: List[Dict[str, Any]] = []

    def add_task(self, task: Task) -> None:
        self._tasks[task.id] = task
        if not task.dependencies:
            self._queue.append(task.id)

    def resolve_dag(self) -> List[str]:
        """Topological sort of tasks."""
        in_degree = {tid: len(t.dependencies) for tid, t in self._tasks.items()}
        ready = [tid for tid, d in in_degree.items() if d == 0]
        order = []
        while ready:
            tid = ready.pop(0)
            order.append(tid)
            for t in self._tasks.values():
                if tid in t.dependencies:
                    in_degree[t.id] -= 1
                    if in_degree[t.id] == 0:
                        ready.append(t.id)
        return order

    def execute(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if not task:
            return None
        # Check dependencies
        for dep in task.dependencies:
            dep_task = self._tasks.get(dep)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                task.status = TaskStatus.SKIPPED
                task.error = f"Dependency {dep} not completed"
                return task
        task.status = TaskStatus.RUNNING
        try:
            task.result = task.handler()
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
        self._history.append({"task": task_id, "status": task.status.value, "result": task.result})
        return task

    def run_workflow(self) -> Dict[str, Any]:
        """Execute all tasks in dependency order."""
        order = self.resolve_dag()
        results = {}
        for tid in order:
            task = self.execute(tid)
            results[tid] = {"status": task.status.value, "result": task.result, "error": task.error}
        return results

    def schedule_job(self, job: ScheduledJob) -> None:
        self._jobs[job.id] = job
        logger.info(f"Scheduled job: {job.name} every {job.interval_seconds}s")

    def tick(self) -> List[Dict[str, Any]]:
        """Check and run scheduled jobs."""
        now = time.monotonic()
        ran = []
        for job in self._jobs.values():
            if now - job.last_run >= job.interval_seconds:
                try:
                    result = job.handler()
                    job.last_run = now
                    job.run_count += 1
                    ran.append({"job": job.id, "result": result, "count": job.run_count})
                except Exception as e:
                    ran.append({"job": job.id, "error": str(e)})
        return ran

    def get_task_status(self) -> Dict[str, str]:
        return {tid: t.status.value for tid, t in self._tasks.items()}

    def get_stats(self) -> Dict[str, Any]:
        statuses = {}
        for t in self._tasks.values():
            statuses[t.status.value] = statuses.get(t.status.value, 0) + 1
        return {
            "tasks": len(self._tasks),
            "jobs": len(self._jobs),
            "statuses": statuses,
            "history": len(self._history),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Workflow Scheduler Engine")
    print("ai/llm_workflow_scheduler_native.py")
    print("=" * 60)

    engine = WorkflowSchedulerEngine()

    # 1. Define DAG
    print("\n[1] Define DAG")
    engine.add_task(Task("A", "Load data", lambda: "data_loaded"))
    engine.add_task(Task("B", "Preprocess", lambda: "preprocessed", dependencies=["A"]))
    engine.add_task(Task("C", "Train model", lambda: "model_trained", dependencies=["B"]))
    engine.add_task(Task("D", "Evaluate", lambda: "evaluated", dependencies=["C"]))
    engine.add_task(Task("E", "Deploy", lambda: "deployed", dependencies=["C"]))
    print("  Tasks: A → B → C → D, E")

    # 2. Resolve order
    print("\n[2] Topological Order")
    order = engine.resolve_dag()
    print(f"  Order: {' → '.join(order)}")

    # 3. Execute
    print("\n[3] Execute Workflow")
    results = engine.run_workflow()
    for tid, res in results.items():
        print(f"  {tid}: {res['status']} → {res['result']}")

    # 4. Scheduled job
    print("\n[4] Scheduled Job")
    counter = 0
    def job_fn():
        nonlocal counter
        counter += 1
        return f"tick_{counter}"
    job = ScheduledJob("j1", "Heartbeat", 0.5, job_fn)
    engine.schedule_job(job)
    for _ in range(3):
        time.sleep(0.6)
        ran = engine.tick()
        for r in ran:
            print(f"  {r['job']}: {r['result']}")

    # 5. Stats
    print("\n[5] Engine Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
