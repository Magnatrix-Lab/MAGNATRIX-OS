"""
gjc_workflow_engine_native.py
MAGNATRIX-OS — GJC Workflow Engine

Inspired by gajae-code: deep-interview -> ralplan -> ultragoal workflow. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class WorkflowStage:
    stage_id: str
    name: str
    status: str  # pending, active, completed, failed
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""


class GJCWorkflowEngine:
    """deep-interview -> ralplan -> ultragoal workflow engine."""

    STAGES = ["deep-interview", "ralplan", "ultragoal"]

    def __init__(self, cache_dir: str = "./gjc_workflow"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.workflows: Dict[str, List[WorkflowStage]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "workflows.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for wid, wlist in data.items():
                        self.workflows[wid] = [WorkflowStage(**s) for s in wlist]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "workflows.json", "w", encoding="utf-8") as f:
            json.dump(
                {wid: [asdict(s) for s in wlist] for wid, wlist in self.workflows.items()}, f, indent=2,
            )

    def create_workflow(self, workflow_id: str, requirements: str) -> List[WorkflowStage]:
        """Create a new workflow with all stages."""
        stages = []
        for i, stage_name in enumerate(self.STAGES):
            stage = WorkflowStage(
                stage_id=f"{workflow_id}_{stage_name}", name=stage_name, status="pending",
                input_data={"requirements": requirements} if i == 0 else {},
            )
            stages.append(stage)
        self.workflows[workflow_id] = stages
        self._save()
        return stages

    def start_stage(self, workflow_id: str, stage_id: str) -> bool:
        for stage in self.workflows.get(workflow_id, []):
            if stage.stage_id == stage_id:
                stage.status = "active"
                stage.started_at = datetime.now().isoformat()
                self._save()
                return True
        return False

    def complete_stage(self, workflow_id: str, stage_id: str, output: Dict[str, Any]) -> bool:
        for stage in self.workflows.get(workflow_id, []):
            if stage.stage_id == stage_id:
                stage.status = "completed"
                stage.output_data = output
                stage.completed_at = datetime.now().isoformat()
                self._save()
                return True
        return False

    def get_workflow(self, workflow_id: str) -> List[WorkflowStage]:
        return self.workflows.get(workflow_id, [])

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.workflows)
        completed = sum(1 for w in self.workflows.values() if all(s.status == "completed" for s in w))
        return {"total_workflows": total, "completed": completed}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["GJCWorkflowEngine", "WorkflowStage"]