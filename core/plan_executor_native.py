"""
plan_executor_native.py
MAGNATRIX-OS — Plan Executor

Inspired by engineering-discipline: Worker-validator execution loop. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ExecutionResult:
    result_id: str
    plan_id: str
    step_id: str
    success: bool
    output: str
    error: str
    duration_ms: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class PlanExecutor:
    """Worker-validator execution loop for plans."""

    def __init__(self, cache_dir: str = "./execution_results"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, List[ExecutionResult]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, rlist in data.items():
                        self.results[pid] = [ExecutionResult(**r) for r in rlist]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump(
                {pid: [asdict(r) for r in rlist] for pid, rlist in self.results.items()}, f, indent=2,
            )

    def execute_step(self, plan_id: str, step_id: str, action: str) -> ExecutionResult:
        """Execute a plan step and record result."""
        import time
        start = time.time()
        # Simulate execution
        success = "error" not in action.lower() and "fail" not in action.lower()
        output = f"Executed: {action}" if success else f"Failed: {action}"
        error = "" if success else "Execution error"
        duration = (time.time() - start) * 1000
        result = ExecutionResult(
            result_id=f"{plan_id}_{step_id}", plan_id=plan_id, step_id=step_id,
            success=success, output=output, error=error, duration_ms=round(duration, 2),
        )
        self.results.setdefault(plan_id, []).append(result)
        self._save()
        return result

    def validate(self, plan_id: str) -> Dict[str, Any]:
        """Validate all results for a plan."""
        results = self.results.get(plan_id, [])
        all_pass = all(r.success for r in results)
        total = len(results)
        passed = sum(1 for r in results if r.success)
        avg_time = sum(r.duration_ms for r in results) / max(1, total)
        return {
            "plan_id": plan_id, "all_pass": all_pass, "total": total,
            "passed": passed, "failed": total - passed, "avg_duration_ms": round(avg_time, 2),
        }

    def get_results(self, plan_id: str) -> List[ExecutionResult]:
        return self.results.get(plan_id, [])

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(r) for r in self.results.values())
        passed = sum(1 for rlist in self.results.values() for r in rlist if r.success)
        return {"total_executions": total, "passed": passed, "failed": total - passed}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["PlanExecutor", "ExecutionResult"]