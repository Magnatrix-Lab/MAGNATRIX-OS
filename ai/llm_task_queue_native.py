"""
llm_task_queue_native.py
MAGNATRIX-OS Task Queue Engine
Native Python, stdlib only.
Provides async task queue with priority scheduling, worker pools, retries,
dead-letter handling, and progress tracking.
"""

from __future__ import annotations

import json
import queue
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class Task:
    id: str
    name: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retries: int = 0
    max_retries: int = 3
    error_log: List[str] = field(default_factory=list)
    result: Optional[Any] = None
    worker_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "payload": self.payload,
            "priority": self.priority.name,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "error_log": self.error_log,
            "result": self.result,
            "worker_id": self.worker_id,
            "tags": self.tags,
        }


@dataclass
class QueueStats:
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    dead_letter: int = 0
    total_processed: int = 0
    avg_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TaskQueueEngine:
    """
    Priority task queue with worker pool and retry management.
    """

    def __init__(self, max_workers: int = 4, name: str = "default") -> None:
        self.name = name
        self.max_workers = max_workers
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._tasks: Dict[str, Task] = {}
        self._dead_letter: List[Task] = []
        self._handlers: Dict[str, Callable[[Task], Any]] = {}
        self._lock = threading.Lock()
        self._workers: List[threading.Thread] = []
        self._stop_event = threading.Event()
        self._stats = QueueStats()
        self._latencies: List[float] = []
        self._started = False

    def register_handler(self, task_name: str, handler: Callable[[Task], Any]) -> None:
        self._handlers[task_name] = handler

    def submit(
        self, name: str, payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3, tags: Optional[List[str]] = None
    ) -> Task:
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            id=task_id, name=name, payload=payload,
            priority=priority, max_retries=max_retries,
            tags=tags or [], status=TaskStatus.QUEUED
        )
        with self._lock:
            self._tasks[task_id] = task
        # Lower priority value = higher priority in queue
        self._queue.put((priority.value, task_id))
        return task

    def _worker_loop(self, worker_id: str) -> None:
        while not self._stop_event.is_set():
            try:
                priority, task_id = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            with self._lock:
                task = self._tasks.get(task_id)
                if not task or task.status not in (TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RETRYING):
                    continue
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                task.worker_id = worker_id
                self._stats.running += 1

            handler = self._handlers.get(task.name)
            try:
                if handler:
                    result = handler(task)
                else:
                    raise ValueError(f"No handler registered for task: {task.name}")
                with self._lock:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = time.time()
                    task.result = result
                    self._stats.completed += 1
                    self._stats.running -= 1
                    self._stats.total_processed += 1
                    latency = (task.completed_at - task.created_at) * 1000
                    self._latencies.append(latency)
            except Exception as e:
                error_msg = f"{e}\n{traceback.format_exc()}"
                with self._lock:
                    task.error_log.append(error_msg)
                    task.retries += 1
                    if task.retries > task.max_retries:
                        task.status = TaskStatus.DEAD_LETTER
                        self._dead_letter.append(task)
                        self._stats.dead_letter += 1
                        self._stats.failed += 1
                        self._stats.running -= 1
                    else:
                        task.status = TaskStatus.RETRYING
                        self._queue.put((task.priority.value, task.id))
                        self._stats.running -= 1
            finally:
                self._queue.task_done()

    def start(self) -> None:
        if self._started:
            return
        self._stop_event.clear()
        for i in range(self.max_workers):
            t = threading.Thread(target=self._worker_loop, args=(f"worker-{i}",), daemon=True)
            t.start()
            self._workers.append(t)
        self._started = True

    def stop(self, wait: bool = True, timeout: Optional[float] = None) -> None:
        self._stop_event.set()
        if wait:
            for w in self._workers:
                w.join(timeout=timeout or 5.0)
        self._started = False

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        with self._lock:
            tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def get_dead_letter(self) -> List[Task]:
        return list(self._dead_letter)

    def get_stats(self) -> QueueStats:
        with self._lock:
            stats = QueueStats(
                pending=self._queue.qsize(),
                running=self._stats.running,
                completed=self._stats.completed,
                failed=self._stats.failed,
                dead_letter=self._stats.dead_letter,
                total_processed=self._stats.total_processed,
            )
            if self._latencies:
                stats.avg_latency_ms = sum(self._latencies) / len(self._latencies)
            return stats

    def retry_dead_letter(self, task_id: str) -> bool:
        for task in self._dead_letter:
            if task.id == task_id:
                task.status = TaskStatus.QUEUED
                task.retries = 0
                task.error_log.clear()
                self._dead_letter.remove(task)
                with self._lock:
                    self._tasks[task_id] = task
                self._queue.put((task.priority.value, task.id))
                return True
        return False

    def wait_until_empty(self, timeout: Optional[float] = None) -> bool:
        start = time.time()
        while not self._queue.empty():
            if timeout and (time.time() - start) > timeout:
                return False
            time.sleep(0.1)
        return True

    def export_state(self, path: str) -> None:
        with self._lock:
            data = {
                "tasks": [t.to_dict() for t in self._tasks.values()],
                "dead_letter": [t.to_dict() for t in self._dead_letter],
                "stats": self._stats.to_dict(),
            }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Task Queue Engine")
    print("=" * 60)

    engine = TaskQueueEngine(max_workers=2, name="llm_tasks")

    # Register handlers
    def summarize_handler(task: Task) -> str:
        text = task.payload.get("text", "")
        return f"Summary: {text[:50]}..."

    def translate_handler(task: Task) -> str:
        text = task.payload.get("text", "")
        lang = task.payload.get("lang", "en")
        return f"[{lang}] {text}"

    def fail_once_handler(task: Task) -> str:
        if task.retries == 0:
            raise RuntimeError("Simulated failure")
        return "Recovered after retry"

    engine.register_handler("summarize", summarize_handler)
    engine.register_handler("translate", translate_handler)
    engine.register_handler("fail_once", fail_once_handler)

    engine.start()

    print("\n--- Submitting Tasks ---")
    t1 = engine.submit("summarize", {"text": "This is a long article about AI systems." * 10}, priority=TaskPriority.HIGH)
    t2 = engine.submit("translate", {"text": "Halo dunia", "lang": "en"}, priority=TaskPriority.NORMAL)
    t3 = engine.submit("fail_once", {"data": "x"}, priority=TaskPriority.CRITICAL, max_retries=2)
    t4 = engine.submit("summarize", {"text": "Another article."}, priority=TaskPriority.LOW)

    print(f"  Submitted: {t1.id} ({t1.name}) priority={t1.priority.name}")
    print(f"  Submitted: {t2.id} ({t2.name}) priority={t2.priority.name}")
    print(f"  Submitted: {t3.id} ({t3.name}) priority={t3.priority.name}")
    print(f"  Submitted: {t4.id} ({t4.name}) priority={t4.priority.name}")

    print("\n--- Waiting for completion ---")
    engine.wait_until_empty(timeout=10.0)
    time.sleep(0.5)

    print("\n--- Stats ---")
    stats = engine.get_stats()
    for k, v in stats.to_dict().items():
        print(f"  {k}: {v}")

    print("\n--- Task Results ---")
    for t in engine.list_tasks():
        print(f"  [{t.status.value}] {t.name} ({t.id}): result={t.result} retries={t.retries}")
        if t.error_log:
            print(f"    Errors: {len(t.error_log)}")

    print("\n--- Dead Letter ---")
    dl = engine.get_dead_letter()
    print(f"  Count: {len(dl)}")

    engine.stop()
    print("\nTask Queue test complete.")


if __name__ == "__main__":
    run()
