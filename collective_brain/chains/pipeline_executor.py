#!/usr/bin/env python3
"""
pipeline_executor.py — MAGNATRIX Chain/Pipeline Executor
Adaptasi dari konsep STOA Skill Chains: multi-step pipelines
dengan dependency graphs. Skills bisa di-compose jadi chain
yang dieksekusi secara serial atau parallel berdasarkan dependency.

Contoh chain:
  scout.scan → analyst.analyze → guardian.check → executor.execute
  writer.digest (parallel dengan chain di atas)
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Callable, Any, Tuple


@dataclass
class PipelineStep:
    """Satu step dalam pipeline."""
    id: str
    skill: str
    agent: str
    depends_on: List[str] = field(default_factory=list)
    status: str = "pending"  # pending | running | done | failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_ts: Optional[float] = None
    end_ts: Optional[float] = None


@dataclass
class Pipeline:
    """Satu pipeline lengkap dengan dependency graph."""
    name: str
    description: str
    steps: Dict[str, PipelineStep]
    status: str = "pending"
    created_at: float = 0.0
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


class PipelineExecutor:
    """Executor untuk menjalankan pipeline dengan DAG dependency resolution."""

    def __init__(self, skill_registry=None, agent_registry=None):
        self.skill_registry = skill_registry
        self.agent_registry = agent_registry
        self.pipelines: Dict[str, Pipeline] = {}
        self._lock = False

    def define_pipeline(self, name: str, description: str, steps_spec: List[Dict[str, Any]]) -> Pipeline:
        """Definisi pipeline dari spec list.

        steps_spec format:
        [
            {"id": "scan", "skill": "scan-tokens", "agent": "scout", "depends_on": []},
            {"id": "analyze", "skill": "analyze-signal", "agent": "analyst", "depends_on": ["scan"]},
            ...
        ]
        """
        steps: Dict[str, PipelineStep] = {}
        for spec in steps_spec:
            step = PipelineStep(
                id=spec["id"],
                skill=spec["skill"],
                agent=spec["agent"],
                depends_on=spec.get("depends_on", []),
            )
            steps[step.id] = step

        pipeline = Pipeline(
            name=name,
            description=description,
            steps=steps,
            created_at=time.time(),
        )
        self.pipelines[name] = pipeline
        return pipeline

    def _ready_steps(self, pipeline: Pipeline) -> List[str]:
        """Identifikasi steps yang dependency-nya sudah done."""
        ready = []
        for sid, step in pipeline.steps.items():
            if step.status != "pending":
                continue
            deps_done = all(
                pipeline.steps[d].status == "done"
                for d in step.depends_on if d in pipeline.steps
            )
            if deps_done:
                ready.append(sid)
        return ready

    def _has_failed_deps(self, pipeline: Pipeline, step: PipelineStep) -> bool:
        """Cek apakah ada dependency yang failed."""
        return any(
            pipeline.steps[d].status == "failed"
            for d in step.depends_on if d in pipeline.steps
        )

    def execute(self, pipeline_name: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Eksekusi pipeline sampai selesai (blocking)."""
        pipeline = self.pipelines.get(pipeline_name)
        if not pipeline:
            return {"status": "error", "reason": f"Pipeline '{pipeline_name}' not found"}

        pipeline.status = "running"
        pipeline.started_at = time.time()
        executed = set()
        failed = set()

        while True:
            # Mark steps with failed dependencies
            for sid, step in pipeline.steps.items():
                if step.status == "pending" and self._has_failed_deps(pipeline, step):
                    step.status = "failed"
                    step.error = "Dependency failed"
                    failed.add(sid)

            ready = self._ready_steps(pipeline)
            if not ready:
                # No more ready steps — check if all done/failed
                pending = [s for s in pipeline.steps.values() if s.status == "pending"]
                if not pending:
                    break
                # Deadlock detected (circular or missing deps)
                for s in pending:
                    s.status = "failed"
                    s.error = "Deadlock or missing dependency"
                break

            # Execute ready steps (parallel capable, here sequential for simplicity)
            for sid in ready:
                step = pipeline.steps[sid]
                step.status = "running"
                step.start_ts = time.time()

                # Simulate execution
                success, result = self._run_step(step, context or {})

                step.end_ts = time.time()
                if success:
                    step.status = "done"
                    step.result = result
                    executed.add(sid)
                else:
                    step.status = "failed"
                    step.error = result.get("error", "Unknown error")
                    failed.add(sid)

        pipeline.finished_at = time.time()
        pipeline.status = "done" if not failed else "partial" if executed else "failed"

        return {
            "pipeline": pipeline_name,
            "status": pipeline.status,
            "executed": list(executed),
            "failed": list(failed),
            "duration": round(pipeline.finished_at - pipeline.started_at, 3) if pipeline.finished_at and pipeline.started_at else 0,
        }

    def _run_step(self, step: PipelineStep, context: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Jalankan satu step. Di production, ini akan invoke skill/LLM/agent."""
        # Placeholder execution logic
        # Dalam integrasi penuh, ini akan:
        #   1. Ambil skill dari SkillRegistry
        #   2. Render prompt dengan context
        #   3. Kirim ke agent mesh atau LLM router
        #   4. Parse output dan return
        return True, {
            "step_id": step.id,
            "skill": step.skill,
            "agent": step.agent,
            "executed_at": time.time(),
            "context_keys": list(context.keys()),
        }

    def get_pipeline_status(self, pipeline_name: str) -> Dict[str, Any]:
        pipeline = self.pipelines.get(pipeline_name)
        if not pipeline:
            return {"error": "Pipeline not found"}
        return {
            "name": pipeline.name,
            "description": pipeline.description,
            "status": pipeline.status,
            "created_at": pipeline.created_at,
            "started_at": pipeline.started_at,
            "finished_at": pipeline.finished_at,
            "steps": {
                sid: {
                    "skill": s.skill,
                    "agent": s.agent,
                    "status": s.status,
                    "duration": round(s.end_ts - s.start_ts, 3) if s.end_ts and s.start_ts else None,
                    "error": s.error,
                }
                for sid, s in pipeline.steps.items()
            },
        }

    def list_pipelines(self) -> List[str]:
        return list(self.pipelines.keys())


# ===================================================================
# Demo
# ===================================================================
if __name__ == "__main__":
    import json

    print("=" * 60)
    print("MAGNATRIX Pipeline Executor — STOA Adaptation")
    print("=" * 60)

    executor = PipelineExecutor()

    # Define a trading pipeline
    executor.define_pipeline(
        name="trading-signal-pipeline",
        description="End-to-end trading: scan → analyze → check risk → execute",
        steps_spec=[
            {"id": "scan", "skill": "scan-tokens", "agent": "scout", "depends_on": []},
            {"id": "analyze", "skill": "analyze-signal", "agent": "analyst", "depends_on": ["scan"]},
            {"id": "risk_check", "skill": "check-risk", "agent": "guardian", "depends_on": ["analyze"]},
            {"id": "execute", "skill": "execute-trade", "agent": "executor", "depends_on": ["risk_check"]},
            {"id": "log", "skill": "daily-digest", "agent": "writer", "depends_on": ["execute"]},
        ],
    )

    print("\n[1] Pipeline defined:")
    print(f"  Name: trading-signal-pipeline")
    print(f"  Steps: {len(executor.pipelines['trading-signal-pipeline'].steps)}")

    print("\n[2] Executing pipeline...")
    result = executor.execute("trading-signal-pipeline", context={"market": "crypto", "mode": "demo"})
    print(f"  Status: {result['status']}")
    print(f"  Executed: {result['executed']}")
    print(f"  Failed: {result['failed']}")
    print(f"  Duration: {result['duration']}s")

    print("\n[3] Pipeline status:")
    status = executor.get_pipeline_status("trading-signal-pipeline")
    for sid, s in status["steps"].items():
        print(f"  • {sid:12s} [{s['status']:8s}] agent={s['agent']} skill={s['skill']}")

    # Define a parallel research pipeline
    executor.define_pipeline(
        name="research-parallel",
        description="Parallel research tasks",
        steps_spec=[
            {"id": "arxiv", "skill": "arxiv-scan", "agent": "researcher", "depends_on": []},
            {"id": "github", "skill": "github-trending", "agent": "researcher", "depends_on": []},
            {"id": "synthesize", "skill": "cross-domain-synthesis", "agent": "analyst", "depends_on": ["arxiv", "github"]},
            {"id": "digest", "skill": "daily-digest", "agent": "writer", "depends_on": ["synthesize"]},
        ],
    )

    print("\n[4] Parallel research pipeline:")
    result2 = executor.execute("research-parallel")
    print(f"  Status: {result2['status']}")
    print(f"  Duration: {result2['duration']}s")

    print("\n" + "=" * 60)
    print("Pipeline Executor ready.")
    print("=" * 60)
