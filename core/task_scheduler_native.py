#!/usr/bin/env python3
"""
task_scheduler_native.py
MAGNATRIX-OS — Native Task Scheduler

Cron-style persistent scheduler with job definitions, retry logic (exponential backoff),
execution history, and dependency chains. Writes schedule to disk, survives reboot.
Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import json
import math
import re
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class Job:
    """A scheduled job."""
    job_id: str
    name: str
    schedule: str  # "cron:* * * * *" or "interval:60" or "once:2026-07-01T12:00:00"
    task: str = ""  # Task identifier / command
    dependencies: List[str] = field(default_factory=list)
    retries: int = 3
    backoff_base: float = 2.0
    timeout: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_run: float = 0.0
    next_run: float = 0.0
    run_count: int = 0
    fail_count: int = 0


class TaskSchedulerNative:
    """
    Cron-style persistent scheduler. Supports cron expressions, intervals, one-time jobs,
    dependency chains, and exponential backoff retries. Pure stdlib.
    """

    def __init__(self, workspace: str = "./scheduler") -> None:
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.RLock()
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._tick_interval: int = 10
        self._handlers: Dict[str, Callable[[Job], Any]] = {}
        self._history_path = self.workspace / "history.json"
        self._jobs_path = self.workspace / "jobs.json"
        self._load_jobs()
        self._history: List[Dict[str, Any]] = []
        self._load_history()

    def _load_jobs(self) -> None:
        if self._jobs_path.exists():
            try:
                with open(self._jobs_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for jid, jd in data.items():
                    self._jobs[jid] = Job(**jd)
            except Exception:
                pass

    def _save_jobs(self) -> None:
        with open(self._jobs_path, "w", encoding="utf-8") as f:
            json.dump({jid: asdict(j) for jid, j in self._jobs.items()}, f, indent=2)

    def _load_history(self) -> None:
        if self._history_path.exists():
            try:
                with open(self._history_path, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
            except Exception:
                pass

    def _save_history(self) -> None:
        with open(self._history_path, "w", encoding="utf-8") as f:
            json.dump(self._history[-1000:], f, indent=2)  # Keep last 1000

    def add_job(self, name: str, schedule: str, task: str,
                dependencies: Optional[List[str]] = None,
                retries: int = 3, backoff_base: float = 2.0,
                timeout: int = 300, metadata: Optional[Dict[str, Any]] = None,
                job_id: Optional[str] = None) -> str:
        """
        Add a job. Schedule formats:
        - "cron:* * * * *" — minute hour day month weekday
        - "interval:60" — seconds between runs
        - "once:2026-07-01T12:00:00" — ISO datetime
        """
        with self._lock:
            jid = job_id or f"job_{int(time.time() * 1000)}_{len(self._jobs)}"
            job = Job(
                job_id=jid, name=name, schedule=schedule, task=task,
                dependencies=dependencies or [], retries=retries,
                backoff_base=backoff_base, timeout=timeout,
                metadata=metadata or {}, enabled=True
            )
            job.next_run = self._compute_next_run(job)
            self._jobs[jid] = job
            self._save_jobs()
            return jid

    def remove_job(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                self._save_jobs()
                return True
            return False

    def register_handler(self, task_type: str, handler: Callable[[Job], Any]) -> None:
        """Register a handler for a task type."""
        self._handlers[task_type] = handler

    def start(self) -> None:
        """Start the scheduler loop."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self._scheduler_thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._save_jobs()
            self._save_history()

    def _scheduler_loop(self) -> None:
        while self._running:
            try:
                self._tick()
                time.sleep(self._tick_interval)
            except Exception:
                time.sleep(5)

    def _tick(self) -> None:
        now = time.time()
        with self._lock:
            for job in list(self._jobs.values()):
                if not job.enabled:
                    continue
                if job.next_run <= now:
                    # Check dependencies
                    deps_met = all(
                        self._jobs.get(d) and self._jobs[d].last_run > 0 and self._jobs[d].fail_count == 0
                        for d in job.dependencies
                    )
                    if not deps_met:
                        job.next_run = now + self._tick_interval
                        continue
                    # Execute
                    self._execute_job(job)
                    job.last_run = now
                    job.next_run = self._compute_next_run(job)
            self._save_jobs()

    def _execute_job(self, job: Job) -> None:
        result = {"job_id": job.job_id, "time": time.time(), "status": "running"}
        handler = self._handlers.get(job.task)
        if handler:
            for attempt in range(job.retries + 1):
                try:
                    handler(job)
                    result["status"] = "success"
                    job.run_count += 1
                    break
                except Exception as e:
                    result["status"] = "failed"
                    result["error"] = str(e)
                    result["attempt"] = attempt + 1
                    if attempt < job.retries:
                        backoff = job.backoff_base ** attempt
                        time.sleep(backoff)
                    else:
                        job.fail_count += 1
        else:
            result["status"] = "no_handler"
            job.fail_count += 1
        self._history.append(result)
        self._save_history()

    def _compute_next_run(self, job: Job) -> float:
        now = time.time()
        if job.schedule.startswith("cron:"):
            # Simple cron: next minute alignment
            cron = job.schedule[5:].strip()
            parts = cron.split()
            if len(parts) == 5:
                try:
                    minute = parts[0]
                    if minute == "*":
                        return now + 60
                    elif "/" in minute:
                        step = int(minute.split("/")[1])
                        return now + step * 60
                    else:
                        return now + int(minute) * 60
                except Exception:
                    return now + 60
            return now + 60
        elif job.schedule.startswith("interval:"):
            try:
                seconds = int(job.schedule[9:])
                return now + seconds
            except Exception:
                return now + 60
        elif job.schedule.startswith("once:"):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(job.schedule[5:].replace("Z", "+00:00"))
                return dt.timestamp()
            except Exception:
                return now + 3600
        return now + 60

    def run_now(self, job_id: str) -> Dict[str, Any]:
        """Manually trigger a job immediately."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return {"status": "not_found"}
            self._execute_job(job)
            job.last_run = time.time()
            return {"status": "executed", "job_id": job_id}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "jobs_total": len(self._jobs),
                "jobs_enabled": sum(1 for j in self._jobs.values() if j.enabled),
                "handlers_registered": len(self._handlers),
                "history_entries": len(self._history),
            }

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(j) for j in self._jobs.values()]
