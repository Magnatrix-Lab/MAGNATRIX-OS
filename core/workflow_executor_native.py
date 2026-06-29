"""
workflow_executor_native.py
MAGNATRIX-OS — Workflow Executor

Inspired by AgentSkillOS: Execute DAG workflows with step tracing and progress tracking. Pure stdlib.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ExecutionTrace:
    trace_id: str
    dag_id: str
    node_id: str
    skill_id: str
    status: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    start_time: str = ""
    end_time: str = ""
    duration_ms: float = 0.0
    logs: List[str] = field(default_factory=list)


class WorkflowExecutor:
    """Execute DAG workflows with step tracing and progress tracking."""

    def __init__(self, cache_dir: str = "./workflow_executor"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.traces: Dict[str, List[ExecutionTrace]] = {}
        self.progress: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        for fname in ["traces.json", "progress.json"]:
            f = self.cache_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "traces.json":
                            for tid, tlist in data.items():
                                self.traces[tid] = [ExecutionTrace(**t) for t in tlist]
                        else:
                            self.progress = data
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.cache_dir / "traces.json", "w", encoding="utf-8") as f:
            json.dump(
                {tid: [asdict(t) for t in tlist] for tid, tlist in self.traces.items()}, f, indent=2,
            )
        with open(self.cache_dir / "progress.json", "w", encoding="utf-8") as f:
            json.dump(self.progress, f, indent=2)

    def execute_step(self, execution_id: str, dag_id: str, node_id: str, skill_id: str,
                     inputs: Dict[str, Any]) -> ExecutionTrace:
        start = datetime.now().isoformat()
        t0 = time.time()

        trace = ExecutionTrace(
            trace_id=f"{execution_id}_{node_id}", dag_id=dag_id, node_id=node_id,
            skill_id=skill_id, status="running", input_data=inputs,
            start_time=start,
        )

        # Simulate execution
        trace.logs.append(f"Starting skill: {skill_id}")
        trace.output_data = {"result": f"Output from {skill_id}", "node": node_id}
        trace.status = "completed"
        trace.end_time = datetime.now().isoformat()
        trace.duration_ms = round((time.time() - t0) * 1000, 2)
        trace.logs.append(f"Completed in {trace.duration_ms}ms")

        self.traces.setdefault(execution_id, []).append(trace)
        self._update_progress(execution_id, dag_id)
        self._save()
        return trace

    def _update_progress(self, execution_id: str, dag_id: str) -> None:
        traces = self.traces.get(execution_id, [])
        completed = sum(1 for t in traces if t.status == "completed")
        total = len(traces)
        self.progress[execution_id] = {
            "dag_id": dag_id, "completed": completed, "total": total,
            "percentage": round(completed / max(1, total) * 100, 2),
            "last_updated": datetime.now().isoformat(),
        }

    def get_traces(self, execution_id: str) -> List[ExecutionTrace]:
        return self.traces.get(execution_id, [])

    def get_progress(self, execution_id: str) -> Dict[str, Any]:
        return self.progress.get(execution_id, {})

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(t) for t in self.traces.values())
        completed = sum(1 for tlist in self.traces.values() for t in tlist if t.status == "completed")
        return {"total_executions": len(self.traces), "total_steps": total, "completed_steps": completed}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["WorkflowExecutor", "ExecutionTrace"]