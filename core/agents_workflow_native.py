"""Agents Workflow - Development lifecycle and code preservation rules."""
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class WorkflowStage:
    stage_id: str
    name: str
    status: str = "pending"  # pending, active, completed, failed
    started_at: float = 0.0
    completed_at: float = 0.0
    artifacts: List[str] = field(default_factory=list)
    preservation_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "stage_id": self.stage_id,
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "artifacts": self.artifacts,
            "preservation_rules": self.preservation_rules,
        }


@dataclass
class CodePreservationRule:
    rule_id: str
    pattern: str
    action: str = "preserve"  # preserve, backup, review, warn
    description: str = ""
    severity: str = "medium"

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "pattern": self.pattern,
            "action": self.action,
            "description": self.description,
            "severity": self.severity,
        }


class AgentsWorkflow:
    """Agent development lifecycle manager with code preservation rules."""

    DEFAULT_STAGES = [
        ("plan", "Plan agent architecture and select model"),
        ("build", "Build agent with ADK scaffolding"),
        ("test", "Run local evaluation and tests"),
        ("refine", "Iterate based on eval results"),
        ("deploy", "Deploy to cloud runtime"),
        ("observe", "Monitor and collect telemetry"),
        ("publish", "Register in Gemini Enterprise marketplace"),
    ]

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "agents_workflow"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.stages: Dict[str, WorkflowStage] = {}
        self.preservation_rules: Dict[str, CodePreservationRule] = {}
        self.active_workflows: Dict[str, Dict] = {}
        self._init_default_rules()
        self._load_state()

    def _init_default_rules(self) -> None:
        defaults = [
            ("rule_1", "adk.*agent", "preserve", "ADK agent core code must not be overwritten", "high"),
            ("rule_2", ".*session_state", "backup", "Session state changes require backup", "high"),
            ("rule_3", ".*secret.*", "warn", "Secret management files require review", "critical"),
            ("rule_4", r".*config\.yaml", "preserve", "Configuration files are code-preservation zone", "medium"),
            ("rule_5", r".*tool\.py", "review", "Custom tools require manual review before overwrite", "medium"),
            ("rule_6", ".*test_.*", "backup", "Test files should be backed up before regeneration", "low"),
        ]
        for rid, pat, act, desc, sev in defaults:
            self.preservation_rules[rid] = CodePreservationRule(rule_id=rid, pattern=pat, action=act, description=desc, severity=sev)

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for s in data.get("stages", []):
                    self.stages[s["stage_id"]] = WorkflowStage(**s)
                for w in data.get("workflows", []):
                    self.active_workflows[w["workflow_id"]] = w
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "stages": [s.to_dict() for s in self.stages.values()],
            "workflows": list(self.active_workflows.values()),
            "rules": [r.to_dict() for r in self.preservation_rules.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def create_workflow(self, agent_name: str, model_id: str = "gemini-2.0-flash") -> Dict:
        """Create a new agent development workflow."""
        workflow_id = f"wf_{agent_name}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        workflow = {
            "workflow_id": workflow_id,
            "agent_name": agent_name,
            "model_id": model_id,
            "created_at": time.time(),
            "current_stage": "plan",
            "stages_completed": [],
            "status": "active",
        }
        for sid, sdesc in self.DEFAULT_STAGES:
            stage = WorkflowStage(stage_id=f"{workflow_id}_{sid}", name=sdesc, status="pending")
            self.stages[stage.stage_id] = stage
        self.active_workflows[workflow_id] = workflow
        self._save_state()
        return workflow

    def advance_stage(self, workflow_id: str, stage_name: str) -> WorkflowStage:
        """Advance workflow to next stage."""
        stage_id = f"{workflow_id}_{stage_name}"
        if stage_id not in self.stages:
            raise ValueError(f"Stage {stage_name} not found in workflow")
        stage = self.stages[stage_id]
        stage.status = "completed"
        stage.completed_at = time.time()
        if stage.started_at == 0.0:
            stage.started_at = time.time()
        self.active_workflows[workflow_id]["stages_completed"].append(stage_name)
        self._save_state()
        return stage

    def start_stage(self, workflow_id: str, stage_name: str) -> WorkflowStage:
        """Start a workflow stage."""
        stage_id = f"{workflow_id}_{stage_name}"
        if stage_id not in self.stages:
            raise ValueError(f"Stage {stage_name} not found")
        stage = self.stages[stage_id]
        stage.status = "active"
        stage.started_at = time.time()
        self.active_workflows[workflow_id]["current_stage"] = stage_name
        self._save_state()
        return stage

    def check_preservation(self, file_path: str) -> List[CodePreservationRule]:
        """Check if a file matches any preservation rules."""
        import re
        matched = []
        for rule in self.preservation_rules.values():
            if re.search(rule.pattern, file_path):
                matched.append(rule)
        return matched

    def add_preservation_rule(self, pattern: str, action: str, description: str, severity: str = "medium") -> CodePreservationRule:
        rule_id = f"rule_{hashlib.md5(pattern.encode()).hexdigest()[:8]}"
        rule = CodePreservationRule(rule_id=rule_id, pattern=pattern, action=action, description=description, severity=severity)
        self.preservation_rules[rule_id] = rule
        self._save_state()
        return rule

    def get_workflow_progress(self, workflow_id: str) -> Dict:
        """Get progress percentage and current status."""
        wf = self.active_workflows.get(workflow_id, {})
        completed = len(wf.get("stages_completed", []))
        total = len(self.DEFAULT_STAGES)
        return {
            "workflow_id": workflow_id,
            "progress_pct": round(completed / total * 100, 1),
            "current_stage": wf.get("current_stage", "unknown"),
            "status": wf.get("status", "unknown"),
            "stages_completed": completed,
            "stages_total": total,
        }

    def get_stats(self) -> Dict:
        active = sum(1 for w in self.active_workflows.values() if w.get("status") == "active")
        completed = sum(1 for w in self.active_workflows.values() if w.get("status") == "completed")
        return {
            "workflows_active": active,
            "workflows_completed": completed,
            "workflows_total": len(self.active_workflows),
            "stages_total": len(self.stages),
            "preservation_rules": len(self.preservation_rules),
        }

    def to_dict(self) -> Dict:
        return {
            "workflows": list(self.active_workflows.values()),
            "stages": [s.to_dict() for s in self.stages.values()],
            "rules": [r.to_dict() for r in self.preservation_rules.values()],
            "stats": self.get_stats(),
        }


__all__ = ["AgentsWorkflow", "WorkflowStage", "CodePreservationRule"]
