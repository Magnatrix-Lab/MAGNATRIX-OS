"""
agent_workflow_builder_native.py
MAGNATRIX-OS — Agent Workflow Builder

Inspired by Langflow (langflow-ai): Agent-specific workflow builder with reasoning loops.
Build agent workflows with tool calling, reasoning steps, and memory integration. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class AgentWorkflowStep:
    step_id: str
    step_type: str  # think, tool_call, observe, respond
    description: str
    tool_name: str = ""
    tool_args: Dict[str, Any] = field(default_factory=dict)
    result: str = ""
    status: str = "pending"


@dataclass
class AgentWorkflow:
    workflow_id: str
    name: str
    task: str
    steps: List[AgentWorkflowStep] = field(default_factory=list)
    status: str = "pending"
    final_answer: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class AgentWorkflowBuilder:
    """Build agent workflows with reasoning loops and tool calling."""

    def __init__(self, workflows_dir: str = "./agent_workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.workflows_dir.mkdir(exist_ok=True)
        self.workflows: Dict[str, AgentWorkflow] = {}
        self._load()

    def _load(self) -> None:
        file = self.workflows_dir / "workflows.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for wid, wd in data.items():
                        wd["steps"] = [AgentWorkflowStep(**s) for s in wd.get("steps", [])]
                        self.workflows[wid] = AgentWorkflow(**wd)
            except Exception:
                pass

    def _save(self) -> None:
        out = {}
        for wid, w in self.workflows.items():
            d = asdict(w)
            d["steps"] = [asdict(s) for s in w.steps]
            out[wid] = d
        with open(self.workflows_dir / "workflows.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def create(self, workflow_id: str, name: str, task: str) -> AgentWorkflow:
        wf = AgentWorkflow(workflow_id=workflow_id, name=name, task=task)
        self.workflows[workflow_id] = wf
        self._save()
        return wf

    def add_think_step(self, workflow_id: str, step_id: str, description: str) -> bool:
        wf = self.workflows.get(workflow_id)
        if not wf:
            return False
        step = AgentWorkflowStep(step_id=step_id, step_type="think", description=description)
        wf.steps.append(step)
        self._save()
        return True

    def add_tool_step(self, workflow_id: str, step_id: str, description: str, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        wf = self.workflows.get(workflow_id)
        if not wf:
            return False
        step = AgentWorkflowStep(
            step_id=step_id, step_type="tool_call", description=description,
            tool_name=tool_name, tool_args=tool_args,
        )
        wf.steps.append(step)
        self._save()
        return True

    def add_respond_step(self, workflow_id: str, step_id: str, description: str) -> bool:
        wf = self.workflows.get(workflow_id)
        if not wf:
            return False
        step = AgentWorkflowStep(step_id=step_id, step_type="respond", description=description)
        wf.steps.append(step)
        self._save()
        return True

    def complete_step(self, workflow_id: str, step_id: str, result: str) -> bool:
        wf = self.workflows.get(workflow_id)
        if not wf:
            return False
        for s in wf.steps:
            if s.step_id == step_id:
                s.result = result
                s.status = "completed"
                self._save()
                return True
        return False

    def finalize(self, workflow_id: str, final_answer: str) -> bool:
        wf = self.workflows.get(workflow_id)
        if not wf:
            return False
        wf.final_answer = final_answer
        wf.status = "completed"
        self._save()
        return True

    def get_workflow(self, workflow_id: str) -> Optional[AgentWorkflow]:
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> List[AgentWorkflow]:
        return list(self.workflows.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.workflows)
        completed = sum(1 for w in self.workflows.values() if w.status == "completed")
        return {"total": total, "completed": completed}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AgentWorkflowBuilder", "AgentWorkflow", "AgentWorkflowStep"]