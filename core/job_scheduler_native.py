#!/usr/bin/env python3
"""
Background Job Scheduler / Cron Engine for MAGNATRIX-OS
Scheduled tasks, recurring jobs, delayed execution, retry backoff.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import functools
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


@dataclass
class Job:
    """A scheduled job."""
    id: str
    name: str
    func: Callable[..., Any]
    args: Tuple[Any, ...] = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None  # cron-like or interval
    interval_seconds: Optional[int] = None
    delay_seconds: Optional[int] = None
    max_retries: int = 3
    retry_count: int = 0
    retry_backoff: str = "exponential"  # none, linear, exponential
    state: str = "pending"  # pending, scheduled, running, success, failed, retrying
    last_run: float = 0.0
    next_run: float = 0.0
    error: Optional[str] = None
    result: Any = None
    created_at: float = field(default_factory=time.time)


class CronParser:
    """Parse cron-like expressions."""

    # Format: "min hour day month weekday" or shortcuts
    SHORTCUTS = {
        "@yearly":   "0 0 1 1 *",
        "@annually": "0 0 1 1 *",
        "@monthly":  "0 0 1 * *",
        "@weekly":   "0 0 * * 0",
        "@daily":    "0 0 * * *",
        "@hourly":   "0 * * * *",
        "@reboot":   "@reboot",
    }

    @classmethod
    def parse(cls, expression: str) -> Optional[Dict[str, Any]]:
        expr = cls.SHORTCUTS.get(expression, expression)
        if expr == "@reboot":
            return {"type": "reboot"}
        parts = expr.split()
        if len(parts) != 5:
            return None
        return {
            "type": "cron",
            "minute": cls._parse_field(parts[0], 0, 59),
            "hour": cls._parse_field(parts[1], 0, 23),
            "day": cls._parse_field(parts[2], 1, 31),
            "month": cls._parse_field(parts[3], 1, 12),
            "weekday": cls._parse_field(parts[4], 0, 6),
        }

    @classmethod
    def _parse_field(cls, field: str, min_val: int, max_val: int) -> List[int]:
        if field == "*":
            return list(range(min_val, max_val + 1))
        if "/" in field:
            base, step = field.split("/")
            step = int(step)
            vals = cls._parse_field(base, min_val, max_val)
            return vals[::step]
        if "," in field:
            return [int(v) for v in field.split(",")]
        if "-" in field:
            start, end = field.split("-")
            return list(range(int(start), int(end) + 1))
        return [int(field)]

    @classmethod
    def next_run(cls, parsed: Dict[str, Any], now: float) -> float:
        """Calculate next run time from parsed cron."""
        if parsed["type"] == "reboot":
            return now
        tm = time.localtime(now)
        # Simple brute force: check next 366 days
        for day_offset in range(366 * 24 * 60):
            check = now + day_offset * 60
            tm = time.localtime(check)
            if tm.tm_min in parsed["minute"] and \
               tm.tm_hour in parsed["hour"] and \
               tm.tm_mday in parsed["day"] and \
               tm.tm_mon in parsed["month"] and \
               tm.tm_wday in parsed["weekday"]:
                return check
        return now + 86400


class JobScheduler:
    """Main scheduler engine."""

    def __init__(self, store_dir: Optional[str] = None) -> None:
        self.store_dir = Path(store_dir) if store_dir else Path("./jobs")
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: Dict[str, Job] = {}
        self._running = False
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._check_interval = 1.0
        self._history: List[Dict[str, Any]] = []
        self._on_complete: Optional[Callable[[Job], None]] = None

    def schedule(self, job: Job) -> str:
        """Schedule a new job."""
        with self._lock:
            if job.delay_seconds:
                job.next_run = time.time() + job.delay_seconds
            elif job.interval_seconds:
                job.next_run = time.time() + job.interval_seconds
            elif job.schedule:
                parsed = CronParser.parse(job.schedule)
                if parsed:
                    job.next_run = CronParser.next_run(parsed, time.time())
            self._jobs[job.id] = job
            self._persist()
            return job.id

    def add_interval_job(self, name: str, func: Callable, interval: int, args: Tuple = (), kwargs: Dict = None, max_retries: int = 3) -> str:
        job = Job(
            id=f"job_{int(time.time() * 1000)}_{id(func)}",
            name=name, func=func, args=args, kwargs=kwargs or {},
            interval_seconds=interval, max_retries=max_retries,
        )
        return self.schedule(job)

    def add_cron_job(self, name: str, func: Callable, cron: str, args: Tuple = (), kwargs: Dict = None, max_retries: int = 3) -> str:
        job = Job(
            id=f"job_{int(time.time() * 1000)}_{id(func)}",
            name=name, func=func, args=args, kwargs=kwargs or {},
            schedule=cron, max_retries=max_retries,
        )
        return self.schedule(job)

    def add_delayed_job(self, name: str, func: Callable, delay: int, args: Tuple = (), kwargs: Dict = None, max_retries: int = 3) -> str:
        job = Job(
            id=f"job_{int(time.time() * 1000)}_{id(func)}",
            name=name, func=func, args=args, kwargs=kwargs or {},
            delay_seconds=delay, max_retries=max_retries,
        )
        return self.schedule(job)

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                self._persist()
                return True
            return False

    def _execute_job(self, job: Job) -> None:
        job.state = "running"
        job.last_run = time.time()
        try:
            job.result = job.func(*job.args, **job.kwargs)
            job.state = "success"
            job.retry_count = 0
        except Exception as e:
            job.error = str(e)
            job.retry_count += 1
            if job.retry_count <= job.max_retries:
                job.state = "retrying"
                backoff = self._calc_backoff(job)
                job.next_run = time.time() + backoff
            else:
                job.state = "failed"
        self._record_history(job)
        if self._on_complete:
            self._on_complete(job)

    def _calc_backoff(self, job: Job) -> int:
        if job.retry_backoff == "exponential":
            return 2 ** job.retry_count
        elif job.retry_backoff == "linear":
            return job.retry_count * 5
        return 1

    def _record_history(self, job: Job) -> None:
        entry = {
            "job_id": job.id, "name": job.name, "state": job.state,
            "time": time.time(), "error": job.error, "result": str(job.result)[:100],
        }
        self._history.append(entry)
        if len(self._history) > 1000:
            self._history = self._history[-500:]

    def _run_loop(self) -> None:
        while self._running:
            now = time.time()
            with self._lock:
                jobs_to_run = [j for j in self._jobs.values() if j.next_run <= now and j.state in ("pending", "scheduled", "retrying")]
            for job in jobs_to_run:
                job.state = "scheduled"
                # Execute in thread pool
                threading.Thread(target=self._execute_job, args=(job,), daemon=True).start()
                # Update next run for interval jobs
                if job.interval_seconds and job.state != "retrying":
                    job.next_run = now + job.interval_seconds
            time.sleep(self._check_interval)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="JobScheduler")
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _persist(self) -> None:
        """Save job list to disk."""
        data = {
            "jobs": [
                {
                    "id": j.id, "name": j.name, "schedule": j.schedule,
                    "interval_seconds": j.interval_seconds, "delay_seconds": j.delay_seconds,
                    "max_retries": j.max_retries, "retry_count": j.retry_count,
                    "state": j.state, "last_run": j.last_run, "next_run": j.next_run,
                    "error": j.error, "created_at": j.created_at,
                }
                for j in self._jobs.values()
            ]
        }
        (self.store_dir / "jobs.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self) -> None:
        """Load persisted jobs."""
        path = self.store_dir / "jobs.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                # Jobs are loaded but func references are lost - they'd need to be re-registered
            except Exception:
                pass

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": j.id, "name": j.name, "state": j.state,
                    "next_run": j.next_run, "last_run": j.last_run,
                    "retries": j.retry_count, "max_retries": j.max_retries,
                }
                for j in self._jobs.values()
            ]

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._history[-limit:]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            states = {}
            for j in self._jobs.values():
                states[j.state] = states.get(j.state, 0) + 1
            return {
                "total_jobs": len(self._jobs),
                "states": states,
                "history_entries": len(self._history),
                "running": self._running,
            }

    def on_complete(self, callback: Callable[[Job], None]) -> None:
        self._on_complete = callback


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Background Job Scheduler / Cron Engine Demo ===\n")
    scheduler = JobScheduler()
    scheduler.start()

    # Add various job types
    def task_a():
        print("[Job] Task A executed!")
        return "a_done"
    def task_b():
        print("[Job] Task B executed!")
        return "b_done"
    def task_fail():
        raise Exception("Simulated failure")
    def task_recurring():
        print("[Job] Recurring task executed!")
        return "recurring"

    print("Adding interval job (every 2s)...")
    scheduler.add_interval_job("recurring", task_recurring, interval=2)

    print("Adding delayed job (3s delay)...")
    scheduler.add_delayed_job("delayed_a", task_a, delay=3)

    print("Adding cron job (@hourly)...")
    scheduler.add_cron_job("hourly_b", task_b, cron="@hourly")

    print("Adding retry job (will fail)...")
    scheduler.add_delayed_job("failing", task_fail, delay=1, max_retries=2)

    print("\nWaiting 5 seconds...")
    time.sleep(5)

    print(f"\nStats: {scheduler.stats()}")
    print(f"Jobs: {scheduler.list_jobs()}")
    print(f"History (last 5): {scheduler.get_history(5)}")

    scheduler.stop()
    print("\nScheduler stopped.")


if __name__ == "__main__":
    _demo()
