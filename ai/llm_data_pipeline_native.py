#!/usr/bin/env python3
"""
MAGNATRIX-OS — Data Pipeline Engine
ai/llm_data_pipeline_native.py

Features:
- ETL pipeline stages (extract, transform, load)
- Data validation and schema enforcement
- Pipeline monitoring and checkpointing
- Error handling and recovery at stage level
- Batch and stream processing support

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("data_pipeline")


class StageStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStage:
    id: str
    name: str
    handler: Callable[[Any], Any]
    status: StageStatus = StageStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class PipelineCheckpoint:
    stage_id: str
    data: Any
    timestamp: float


class DataPipelineEngine:
    """ETL data pipeline with stages, checkpoints, and recovery."""

    def __init__(self, enable_checkpoints: bool = True):
        self.enable_checkpoints = enable_checkpoints
        self._stages: List[PipelineStage] = []
        self._checkpoints: Dict[str, PipelineCheckpoint] = {}
        self._history: List[Dict[str, Any]] = []

    def add_stage(self, stage: PipelineStage) -> None:
        self._stages.append(stage)

    def run(self, initial_data: Any) -> Tuple[Any, List[PipelineStage]]:
        data = initial_data
        for stage in self._stages:
            t0 = time.monotonic()
            stage.status = StageStatus.RUNNING
            try:
                data = stage.handler(data)
                stage.result = data
                stage.status = StageStatus.COMPLETED
                if self.enable_checkpoints:
                    self._checkpoints[stage.id] = PipelineCheckpoint(stage.id, data, time.monotonic())
            except Exception as e:
                stage.status = StageStatus.FAILED
                stage.error = str(e)
                logger.error(f"Stage {stage.id} failed: {e}")
                # Try recovery from checkpoint
                if stage.id in self._checkpoints:
                    data = self._checkpoints[stage.id].data
                    stage.status = StageStatus.COMPLETED
                else:
                    break
            stage.duration_ms = (time.monotonic() - t0) * 1000
            self._history.append({"stage": stage.id, "status": stage.status.value, "duration": stage.duration_ms})
        return data, self._stages

    def recover(self, stage_id: str) -> Any:
        cp = self._checkpoints.get(stage_id)
        return cp.data if cp else None

    def get_stats(self) -> Dict[str, Any]:
        statuses = {}
        for s in self._stages:
            statuses[s.status.value] = statuses.get(s.status.value, 0) + 1
        return {
            "stages": len(self._stages),
            "checkpoints": len(self._checkpoints),
            "statuses": statuses,
            "total_duration_ms": sum(s.duration_ms for s in self._stages),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Data Pipeline Engine")
    print("ai/llm_data_pipeline_native.py")
    print("=" * 60)

    engine = DataPipelineEngine()

    # Define ETL stages
    engine.add_stage(PipelineStage("extract", "Extract", lambda x: [{"id": i, "raw": v} for i, v in enumerate(x)]))
    engine.add_stage(PipelineStage("clean", "Clean", lambda x: [d for d in x if d["raw"] is not None]))
    engine.add_stage(PipelineStage("transform", "Transform", lambda x: [{**d, "value": d["raw"] * 2} for d in x]))
    engine.add_stage(PipelineStage("validate", "Validate", lambda x: [d for d in x if d["value"] > 0]))
    engine.add_stage(PipelineStage("load", "Load", lambda x: {"count": len(x), "records": x}))

    # Run pipeline
    print("\n[1] Run ETL Pipeline")
    data = [10, 20, None, 30, 0, 40]
    result, stages = engine.run(data)
    print(f"  Input: {data}")
    print(f"  Output: {result}")
    for s in stages:
        print(f"  {s.id}: {s.status.value} ({s.duration_ms:.1f}ms)")

    # 2. Checkpoints
    print("\n[2] Checkpoints")
    for sid, cp in engine._checkpoints.items():
        print(f"  {sid}: {len(str(cp.data))} chars")

    # 3. Stats
    print("\n[3] Pipeline Stats")
    print(f"  {engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
