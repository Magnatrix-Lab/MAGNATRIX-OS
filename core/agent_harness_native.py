"""
agent_harness_native.py
MAGNATRIX-OS — Agent Harness

Inspired by Deer-Flow (ByteDance): SuperAgent harness that combines all capabilities.
End-to-end agent harness: task intake, planning, execution, and reporting. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class HarnessRun:
    run_id: str
    task: str
    status: str = "pending"  # pending, planning, executing, completed, failed
    plan: List[str] = field(default_factory=list)
    results: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now().isoformat()


class AgentHarness:
    """End-to-end agent harness: task intake, planning, execution, reporting."""

    def __init__(self, harness_dir: str = "./harness"):
        self.harness_dir = Path(harness_dir)
        self.harness_dir.mkdir(exist_ok=True)
        self.runs: Dict[str, HarnessRun] = {}
        self._load()

    def _load(self) -> None:
        file = self.harness_dir / "runs.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rd in data.items():
                        self.runs[rid] = HarnessRun(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.harness_dir / "runs.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.runs.items()}, f, indent=2)

    def intake(self, run_id: str, task: str) -> HarnessRun:
        """Accept a new task into the harness."""
        run = HarnessRun(run_id=run_id, task=task, status="pending")
        self.runs[run_id] = run
        self._save()
        return run

    def plan(self, run_id: str, steps: List[str]) -> bool:
        """Create an execution plan for the task."""
        run = self.runs.get(run_id)
        if not run or run.status != "pending":
            return False
        run.plan = steps
        run.status = "planning"
        self._save()
        return True

    def execute_step(self, run_id: str, step_result: str, error: Optional[str] = None) -> bool:
        """Record the result of executing a plan step."""
        run = self.runs.get(run_id)
        if not run or run.status not in ("planning", "executing"):
            return False
        run.status = "executing"
        run.results.append(step_result)
        if error:
            run.errors.append(error)
        self._save()
        return True

    def complete(self, run_id: str) -> bool:
        """Mark a run as completed."""
        run = self.runs.get(run_id)
        if not run:
            return False
        run.status = "completed"
        run.completed_at = datetime.now().isoformat()
        self._save()
        return True

    def fail(self, run_id: str, error: str) -> bool:
        """Mark a run as failed."""
        run = self.runs.get(run_id)
        if not run:
            return False
        run.status = "failed"
        run.errors.append(error)
        run.completed_at = datetime.now().isoformat()
        self._save()
        return True

    def get_report(self, run_id: str) -> Dict[str, Any]:
        """Generate a final report for a run."""
        run = self.runs.get(run_id)
        if not run:
            return {}
        return {
            "run_id": run_id, "task": run.task, "status": run.status,
            "plan_steps": len(run.plan), "completed_steps": len(run.results),
            "errors": len(run.errors), "results": run.results,
            "started_at": run.started_at, "completed_at": run.completed_at,
        }

    def get_run(self, run_id: str) -> Optional[HarnessRun]:
        return self.runs.get(run_id)

    def list_runs(self, status: Optional[str] = None) -> List[HarnessRun]:
        if status:
            return [r for r in self.runs.values() if r.status == status]
        return list(self.runs.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.runs)
        completed = sum(1 for r in self.runs.values() if r.status == "completed")
        failed = sum(1 for r in self.runs.values() if r.status == "failed")
        return {"total_runs": total, "completed": completed, "failed": failed, "in_progress": total - completed - failed}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AgentHarness", "HarnessRun"]