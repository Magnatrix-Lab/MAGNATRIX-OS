#!/usr/bin/env python3
"""
Task Queue & Scheduler for MAGNATRIX-OS
Background job processing, priority queue, cron-like scheduling,
retry with exponential backoff, and worker pool management.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class TaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(enum.IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclasses.dataclass(order=True)
class ScheduledTask:
    """A task scheduled for future execution."""
    execute_at: float
    task_id: str = dataclasses.field(compare=False)
    priority: TaskPriority = dataclasses.field(compare=False)
    payload: Dict[str, Any] = dataclasses.field(compare=False, default_factory=dict)
    handler_name: str = dataclasses.field(compare=False, default="")
    retries: int = dataclasses.field(compare=False, default=0)
    max_retries: int = dataclasses.field(compare=False, default=3)
    retry_delay: float = dataclasses.field(compare=False, default=1.0)
    created_at: float = dataclasses.field(compare=False, default_factory=time.time)
    status: TaskStatus = dataclasses.field(compare=False, default=TaskStatus.PENDING)
    result: Any = dataclasses.field(compare=False, default=None)
    error: Optional[str] = dataclasses.field(compare=False, default=None)


class TaskQueueScheduler:
    """Priority task queue with scheduler and worker pool."""

    def __init__(self, max_workers: int = 4, storage_dir: Optional[str] = None) -> None:
        self.max_workers = max_workers
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._tasks: Dict[str, ScheduledTask] = {}
        self._workers: List[threading.Thread] = []
        self._running = False
        self._lock = threading.Lock()
        self._completed_count = 0
        self._failed_count = 0
        self.storage_dir = Path(storage_dir) if storage_dir else None
        if self.storage_dir:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handler(self, name: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        self._handlers[name] = handler

    # ------------------------------------------------------------------
    # Task submission
    # ------------------------------------------------------------------

    def submit(
        self,
        task_id: str,
        handler_name: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        delay_seconds: float = 0.0,
        max_retries: int = 3,
    ) -> ScheduledTask:
        if handler_name not in self._handlers:
            raise ValueError(f"Handler '{handler_name}' not registered")
        execute_at = time.time() + delay_seconds
        task = ScheduledTask(
            execute_at=execute_at,
            task_id=task_id,
            priority=priority,
            payload=payload,
            handler_name=handler_name,
            max_retries=max_retries,
        )
        self._tasks[task_id] = task
        self._queue.put((execute_at, priority.value, task_id))
        self._save()
        return task

    def schedule_cron(
        self,
        task_id: str,
        handler_name: str,
        payload: Dict[str, Any],
        interval_seconds: float,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> ScheduledTask:
        """Submit a task that will auto-reschedule after completion."""
        task = self.submit(task_id, handler_name, payload, priority, delay_seconds=interval_seconds)
        task.metadata = {"cron": True, "interval": interval_seconds}  # type: ignore
        return task

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.status = TaskStatus.CANCELLED
            self._save()
            return True

    # ------------------------------------------------------------------
    # Worker pool
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._running = True
        for i in range(self.max_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True, name=f"TaskWorker-{i}")
            t.start()
            self._workers.append(t)

    def stop(self, wait: bool = True, timeout: Optional[float] = None) -> None:
        self._running = False
        # Unblock workers by injecting sentinel tasks
        for _ in self._workers:
            self._queue.put((0, -1, None))
        if wait and timeout:
            for t in self._workers:
                t.join(timeout=timeout)

    def _worker_loop(self) -> None:
        while self._running:
            try:
                execute_at, priority, task_id = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if task_id is None:
                break  # sentinel
            task = self._tasks.get(task_id)
            if not task or task.status == TaskStatus.CANCELLED:
                continue
            # Sleep until scheduled time
            now = time.time()
            if execute_at > now:
                time.sleep(execute_at - now)
            self._execute_task(task)

    def _execute_task(self, task: ScheduledTask) -> None:
        handler = self._handlers.get(task.handler_name)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"Handler '{task.handler_name}' missing"
            self._failed_count += 1
            return
        task.status = TaskStatus.RUNNING
        try:
            result = handler(task.payload)
            task.result = result
            task.status = TaskStatus.COMPLETED
            self._completed_count += 1
            # Auto-reschedule if cron
            if hasattr(task, "metadata") and task.metadata.get("cron"):  # type: ignore
                interval = task.metadata.get("interval", 60)  # type: ignore
                new_id = f"{task.task_id}_{int(time.time())}"
                self.submit(new_id, task.handler_name, task.payload, task.priority, interval)
        except Exception as exc:
            task.error = str(exc)
            if task.retries < task.max_retries:
                task.retries += 1
                task.status = TaskStatus.RETRYING
                delay = task.retry_delay * (2 ** task.retries)
                self._queue.put((time.time() + delay, task.priority.value, task.task_id))
            else:
                task.status = TaskStatus.FAILED
                self._failed_count += 1
        self._save()

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if not self.storage_dir:
            return
        data = []
        for t in self._tasks.values():
            data.append({
                "task_id": t.task_id,
                "execute_at": t.execute_at,
                "priority": t.priority.value,
                "payload": t.payload,
                "handler_name": t.handler_name,
                "retries": t.retries,
                "max_retries": t.max_retries,
                "retry_delay": t.retry_delay,
                "created_at": t.created_at,
                "status": t.status.value,
                "result": t.result,
                "error": t.error,
            })
        path = self.storage_dir / "tasks.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        if not self.storage_dir:
            return
        path = self.storage_dir / "tasks.json"
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                task = ScheduledTask(
                    execute_at=item["execute_at"],
                    task_id=item["task_id"],
                    priority=TaskPriority(item["priority"]),
                    payload=item.get("payload", {}),
                    handler_name=item["handler_name"],
                    retries=item.get("retries", 0),
                    max_retries=item.get("max_retries", 3),
                    retry_delay=item.get("retry_delay", 1.0),
                    created_at=item["created_at"],
                    status=TaskStatus(item["status"]),
                    result=item.get("result"),
                    error=item.get("error"),
                )
                self._tasks[task.task_id] = task
                if task.status in (TaskStatus.PENDING, TaskStatus.RETRYING):
                    self._queue.put((task.execute_at, task.priority.value, task.task_id))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[ScheduledTask]:
        if status is None:
            return list(self._tasks.values())
        return [t for t in self._tasks.values() if t.status == status]

    def stats(self) -> Dict[str, Any]:
        by_status: Dict[str, int] = {}
        for t in self._tasks.values():
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
        return {
            "total_tasks": len(self._tasks),
            "completed": self._completed_count,
            "failed": self._failed_count,
            "by_status": by_status,
            "max_workers": self.max_workers,
            "running": self._running,
            "queue_depth": self._queue.qsize(),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="magnatrix_tasks_")
    sched = TaskQueueScheduler(max_workers=2, storage_dir=tmp)
    results: List[str] = []

    def _echo_handler(payload: Dict[str, Any]) -> str:
        msg = payload.get("message", "noop")
        results.append(msg)
        return f"echo:{msg}"

    def _fail_handler(payload: Dict[str, Any]) -> str:
        raise RuntimeError("Simulated failure")

    sched.register_handler("echo", _echo_handler)
    sched.register_handler("fail", _fail_handler)

    print("=== Task Queue & Scheduler Demo ===\n")
    sched.start()

    # Submit tasks
    sched.submit("t1", "echo", {"message": "hello"}, priority=TaskPriority.HIGH)
    sched.submit("t2", "echo", {"message": "world"}, priority=TaskPriority.NORMAL, delay_seconds=0.5)
    sched.submit("t3", "fail", {"message": "boom"}, priority=TaskPriority.LOW, max_retries=2)

    # Wait for completion
    time.sleep(2.5)

    print(f"Results: {results}")
    print(f"Task t3 status: {sched.get_task('t3').status.value}")
    print(f"Task t3 retries: {sched.get_task('t3').retries}")
    print(f"Stats: {sched.stats()}")

    sched.stop(wait=False)
    import shutil
    shutil.rmtree(tmp)
    print("\nCleanup complete.")


if __name__ == "__main__":
    _demo()
