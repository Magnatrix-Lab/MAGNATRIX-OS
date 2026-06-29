"""
team_coordinator_native.py
MAGNATRIX-OS — Team Coordinator

Inspired by gajae-code: Coordinate parallel tmux workers for larger tasks. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class WorkerTask:
    task_id: str
    worker_id: str
    description: str
    status: str
    result: str = ""


class TeamCoordinator:
    """Coordinate parallel workers for larger tasks."""

    def __init__(self, cache_dir: str = "./team_coordinator"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.tasks: Dict[str, WorkerTask] = {}
        self.workers: List[str] = []
        self._load()

    def _load(self) -> None:
        for fname, attr in [("tasks.json", "tasks"), ("workers.json", "workers")]:
            f = self.cache_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "tasks.json":
                            for tid, td in data.items():
                                self.tasks[tid] = WorkerTask(**td)
                        else:
                            self.workers = data
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.cache_dir / "tasks.json", "w", encoding="utf-8") as f:
            json.dump({tid: asdict(t) for tid, t in self.tasks.items()}, f, indent=2)
        with open(self.cache_dir / "workers.json", "w", encoding="utf-8") as f:
            json.dump(self.workers, f, indent=2)

    def register_worker(self, worker_id: str) -> None:
        if worker_id not in self.workers:
            self.workers.append(worker_id)
            self._save()

    def assign_task(self, task_id: str, worker_id: str, description: str) -> WorkerTask:
        task = WorkerTask(
            task_id=task_id, worker_id=worker_id, description=description, status="pending",
        )
        self.tasks[task_id] = task
        self._save()
        return task

    def complete_task(self, task_id: str, result: str) -> bool:
        task = self.tasks.get(task_id)
        if task:
            task.status = "completed"
            task.result = result
            self._save()
            return True
        return False

    def get_worker_tasks(self, worker_id: str) -> List[WorkerTask]:
        return [t for t in self.tasks.values() if t.worker_id == worker_id]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        return {"total_tasks": total, "completed": completed, "workers": len(self.workers)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["TeamCoordinator", "WorkerTask"]