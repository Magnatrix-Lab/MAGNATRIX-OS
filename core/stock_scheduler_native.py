"""
stock_scheduler_native.py
MAGNATRIX-OS — Stock Scheduler

Inspired by daily_stock_analysis zero-cost scheduled runs:
Schedule recurring stock analysis tasks with cron-like timing. Pure stdlib.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta


@dataclass
class ScheduledJob:
    job_id: str
    name: str
    task_type: str
    symbols: List[str] = field(default_factory=list)
    schedule: str = "daily"  # daily, hourly, weekly
    hour: int = 9
    minute: int = 0
    last_run: str = ""
    next_run: str = ""
    run_count: int = 0
    is_active: bool = True
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.next_run:
            self._calc_next()

    def _calc_next(self) -> None:
        now = datetime.now()
        if self.schedule == "hourly":
            next_run = now.replace(minute=self.minute, second=0, microsecond=0) + timedelta(hours=1)
        elif self.schedule == "weekly":
            next_run = now + timedelta(days=7 - now.weekday())
            next_run = next_run.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        else:
            next_run = now + timedelta(days=1)
            next_run = next_run.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        self.next_run = next_run.isoformat()


class StockScheduler:
    """Schedule recurring stock analysis tasks."""

    def __init__(self, jobs_dir: str = "./stock_jobs"):
        self.jobs_dir = Path(jobs_dir)
        self.jobs_dir.mkdir(exist_ok=True)
        self.jobs: Dict[str, ScheduledJob] = {}
        self._load()

    def _load(self) -> None:
        file = self.jobs_dir / "jobs.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for jid, jd in data.items():
                        self.jobs[jid] = ScheduledJob(**jd)
            except Exception:
                pass

    def _save(self) -> None:
        file = self.jobs_dir / "jobs.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump({jid: asdict(j) for jid, j in self.jobs.items()}, f, indent=2)

    def create_job(self, job_id: str, name: str, task_type: str, symbols: List[str],
                   schedule: str = "daily", hour: int = 9, minute: int = 0, params: Optional[Dict[str, Any]] = None) -> ScheduledJob:
        job = ScheduledJob(
            job_id=job_id, name=name, task_type=task_type, symbols=symbols,
            schedule=schedule, hour=hour, minute=minute, params=params or {},
        )
        self.jobs[job_id] = job
        self._save()
        return job

    def run_job(self, job_id: str) -> Dict[str, Any]:
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        job.last_run = datetime.now().isoformat()
        job.run_count += 1
        job._calc_next()
        self._save()
        return {
            "job_id": job_id, "name": job.name, "task_type": job.task_type,
            "symbols": job.symbols, "run_count": job.run_count, "next_run": job.next_run,
        }

    def check_due_jobs(self) -> List[ScheduledJob]:
        now = datetime.now().isoformat()
        return [j for j in self.jobs.values() if j.is_active and j.next_run <= now]

    def delete_job(self, job_id: str) -> bool:
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save()
            return True
        return False

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        return self.jobs.get(job_id)

    def list_jobs(self) -> List[ScheduledJob]:
        return list(self.jobs.values())

    def get_stats(self) -> Dict[str, Any]:
        active = sum(1 for j in self.jobs.values() if j.is_active)
        total_runs = sum(j.run_count for j in self.jobs.values())
        return {"total_jobs": len(self.jobs), "active": active, "total_runs": total_runs}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["StockScheduler", "ScheduledJob"]