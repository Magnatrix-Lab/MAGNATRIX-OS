"""
agent_workflow_builder_native.py
MAGNATRIX-OS — Agent Workflow Builder

Inspired by langflow-ai/langflow agent workflows:
Build multi-agent workflows with reasoning, tool use, and delegation. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class AgentStep:
    step_id: str
    agent_name: str
    action: str
    input_data: str
    output_data: str = ""
    tool_used: str = ""
    status: str = "pending"


@dataclass
class AgentWorkflow:
    workflow_id: str
    name: str
    objective: str
    steps: List[AgentStep] = field(default_factory=list)
    agents: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)


class AgentWorkflowBuilder:
    """Build multi-agent workflows with reasoning and tool use."""

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
                        wd["steps"] = [AgentStep(**s) for s in wd.get("steps", [])]
                        self.workflows[wid] = AgentWorkflow(**wd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.workflows_dir / "workflows.json", "w", encoding="utf-8") as f:
            out = {}
            for wid, wf in self.workflows.items():
                d = asdict(wf)
                d["steps"] = [asdict(s) for s in wf.steps]
                out[wid] = d
            json.dump(out, f, indent=2)

    def create_workflow(self, workflow_id: str, name: str, objective: str) -> AgentWorkflow:
        wf = AgentWorkflow(workflow_id=workflow_id, name=name, objective=objective)
        self.workflows[workflow_id] = wf
        self._save()
        return wf

    def add_agent(self, workflow_id: str, agent_name: str) -> bool:
        wf = self.workflows.get(workflow_id)
        if not wf:
            return False
        if agent_name not in wf.agents:
            wf.agents.append(agent_name)
            self._save()
            return True
        return False

    def add_tool(self, workflow_id: str, tool_name: str) -> bool:
        wf = self.workflows.get(workflow_id)
        if not wf:
            return False
        if tool_name not in wf.tools:
            wf.tools.append(tool_name)
            self._save()
            return True
        return False

    def add_step(self, workflow_id: str, step_id: str, agent_name: str, action: str,
                 input_data: str) -> AgentStep:
        wf = self.workflows.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")
        step = AgentStep(step_id=step_id, agent_name=agent_name, action=action, input_data=input_data)
        wf.steps.append(step)
        self._save()
        return step

    def execute_step(self, workflow_id: str, step_id: str, output: str, tool_used: str = "") -> bool:
        wf = self.workflows.get(workflow_id)
        if not wf:
            return False
        for step in wf.steps:
            if step.step_id == step_id:
                step.output_data = output
                step.tool_used = tool_used
                step.status = "completed"
                self._save()
                return True
        return False

    def get_workflow(self, workflow_id: str) -> Optional[AgentWorkflow]:
        return self.workflows.get(workflow_id)

    def get_stats(self) -> Dict[str, Any]:
        total_steps = sum(len(w.steps) for w in self.workflows.values())
        return {"workflows": len(self.workflows), "total_steps": total_steps}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AgentWorkflowBuilder", "AgentWorkflow", "AgentStep"]