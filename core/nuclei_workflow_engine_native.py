"""
nuclei_workflow_engine_native.py
MAGNATRIX-OS — Nuclei Workflow Engine

Inspired by Nuclei template workflows: chain multiple templates together. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class WorkflowStep:
    step_id: str
    template_id: str
    condition: str  # always, if_matched, if_not_matched
    next_steps: List[str] = field(default_factory=list)


@dataclass
class Workflow:
    workflow_id: str
    name: str
    steps: Dict[str, WorkflowStep]
    start_step: str


class NucleiWorkflowEngine:
    """Chain multiple templates together with conditional execution."""

    def __init__(self, cache_dir: str = "./nuclei_workflows"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[str, List[str]] = {}
        self._load()

    def _load(self) -> None:
        for fname in ["workflows.json", "executions.json"]:
            f = self.cache_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "workflows.json":
                            for wid, wd in data.items():
                                steps = {sid: WorkflowStep(**sd) for sid, sd in wd.get("steps", {}).items()}
                                self.workflows[wid] = Workflow(
                                    workflow_id=wid, name=wd["name"], steps=steps, start_step=wd.get("start_step", ""),
                                )
                        else:
                            self.executions = data
                except Exception:
                    pass

    def _save(self) -> None:
        out = {}
        for wid, w in self.workflows.items():
            d = asdict(w)
            d["steps"] = {sid: asdict(s) for sid, s in w.steps.items()}
            out[wid] = d
        with open(self.cache_dir / "workflows.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        with open(self.cache_dir / "executions.json", "w", encoding="utf-8") as f:
            json.dump(self.executions, f, indent=2)

    def create_workflow(self, workflow_id: str, name: str, start_step: str) -> Workflow:
        workflow = Workflow(workflow_id=workflow_id, name=name, steps={}, start_step=start_step)
        self.workflows[workflow_id] = workflow
        self._save()
        return workflow

    def add_step(self, workflow_id: str, step_id: str, template_id: str, condition: str = "always", next_steps: Optional[List[str]] = None) -> bool:
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return False
        workflow.steps[step_id] = WorkflowStep(
            step_id=step_id, template_id=template_id, condition=condition, next_steps=next_steps or [],
        )
        self._save()
        return True

    def execute(self, execution_id: str, workflow_id: str, target: str) -> List[str]:
        """Execute a workflow against a target."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return []
        executed = []
        current = workflow.start_step
        visited = set()
        while current and current not in visited:
            visited.add(current)
            step = workflow.steps.get(current)
            if not step:
                break
            executed.append(step.template_id)
            # In a real system, check if template matched
            # For now, always proceed to next steps
            if step.next_steps:
                current = step.next_steps[0]
            else:
                current = None
        self.executions[execution_id] = executed
        self._save()
        return executed

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self.workflows.get(workflow_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.workflows)
        total_executions = len(self.executions)
        return {"total_workflows": total, "total_executions": total_executions}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["NucleiWorkflowEngine", "Workflow", "WorkflowStep"]