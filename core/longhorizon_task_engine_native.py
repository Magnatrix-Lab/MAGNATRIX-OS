"""
longhorizon_task_engine_native.py
MAGNATRIX-OS — Long-Horizon Task Engine

Inspired by Deer-Flow (ByteDance): Long-horizon SuperAgent task harness.
Break down multi-hour tasks into phases, track progress, and checkpoint. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class TaskPhase:
    phase_id: str
    name: str
    description: str
    status: str = "pending"  # pending, running, completed, failed
    duration_estimate_min: int = 0
    dependencies: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""


@dataclass
class LongHorizonTask:
    task_id: str
    title: str
    description: str
    phases: List[TaskPhase] = field(default_factory=list)
    status: str = "pending"
    created_at: str = ""
    total_duration_min: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class LongHorizonTaskEngine:
    """Break down multi-hour tasks into phases, track progress, and checkpoint."""

    def __init__(self, tasks_dir: str = "./longhorizon_tasks"):
        self.tasks_dir = Path(tasks_dir)
        self.tasks_dir.mkdir(exist_ok=True)
        self.tasks: Dict[str, LongHorizonTask] = {}
        self._load()

    def _load(self) -> None:
        file = self.tasks_dir / "tasks.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for tid, td in data.items():
                        td["phases"] = [TaskPhase(**p) for p in td.get("phases", [])]
                        self.tasks[tid] = LongHorizonTask(**td)
            except Exception:
                pass

    def _save(self) -> None:
        out = {}
        for tid, t in self.tasks.items():
            d = asdict(t)
            d["phases"] = [asdict(p) for p in t.phases]
            out[tid] = d
        with open(self.tasks_dir / "tasks.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def create_task(self, task_id: str, title: str, description: str) -> LongHorizonTask:
        task = LongHorizonTask(task_id=task_id, title=title, description=description)
        self.tasks[task_id] = task
        self._save()
        return task

    def add_phase(self, task_id: str, phase_id: str, name: str, description: str,
                  duration_min: int = 0, dependencies: Optional[List[str]] = None) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        phase = TaskPhase(
            phase_id=phase_id, name=name, description=description,
            duration_estimate_min=duration_min, dependencies=dependencies or [],
        )
        task.phases.append(phase)
        task.total_duration_min += duration_min
        self._save()
        return True

    def start_phase(self, task_id: str, phase_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        for p in task.phases:
            if p.phase_id == phase_id and p.status == "pending":
                # Check dependencies
                deps_met = all(
                    any(dp.phase_id == d and dp.status == "completed" for dp in task.phases)
                    for d in p.dependencies
                )
                if deps_met:
                    p.status = "running"
                    p.started_at = datetime.now().isoformat()
                    task.status = "running"
                    self._save()
                    return True
        return False

    def complete_phase(self, task_id: str, phase_id: str, artifacts: Optional[List[str]] = None) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        for p in task.phases:
            if p.phase_id == phase_id and p.status == "running":
                p.status = "completed"
                p.completed_at = datetime.now().isoformat()
                if artifacts:
                    p.artifacts.extend(artifacts)
                # Check if all phases complete
                if all(ph.status == "completed" for ph in task.phases):
                    task.status = "completed"
                self._save()
                return True
        return False

    def fail_phase(self, task_id: str, phase_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        for p in task.phases:
            if p.phase_id == phase_id and p.status == "running":
                p.status = "failed"
                task.status = "failed"
                self._save()
                return True
        return False

    def checkpoint(self, task_id: str) -> Dict[str, Any]:
        task = self.tasks.get(task_id)
        if not task:
            return {}
        completed = [p.phase_id for p in task.phases if p.status == "completed"]
        running = [p.phase_id for p in task.phases if p.status == "running"]
        pending = [p.phase_id for p in task.phases if p.status == "pending"]
        return {
            "task_id": task_id, "status": task.status,
            "completed": completed, "running": running, "pending": pending,
            "artifacts": [a for p in task.phases for a in p.artifacts],
        }

    def get_task(self, task_id: str) -> Optional[LongHorizonTask]:
        return self.tasks.get(task_id)

    def list_tasks(self) -> List[LongHorizonTask]:
        return list(self.tasks.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        running = sum(1 for t in self.tasks.values() if t.status == "running")
        total_phases = sum(len(t.phases) for t in self.tasks.values())
        return {"tasks": total, "completed": completed, "running": running, "failed": total - completed - running, "phases": total_phases}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["LongHorizonTaskEngine", "LongHorizonTask", "TaskPhase"]