#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Workflow Engine (Layer 6 Extension)
Inspired by: itseffi/agentic-os Workflows/
Markdown-defined workflow parser + executor with stage tracking,
conditional branching, and agent delegation hooks.
================================================================================
Zero-dependency workflow engine using regex-based markdown parsing.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union


# =============================================================================
# Constants
# =============================================================================
WORKFLOW_DIR = "/tmp/magnatrix_workflows"


# =============================================================================
# Data Types
# =============================================================================
class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStage:
    name: str
    description: str = ""
    status: StageStatus = StageStatus.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    outputs: Dict[str, Any] = field(default_factory=dict)
    agent: str = ""  # Agent persona to delegate to
    condition: str = ""  # Skip if condition evaluates false
    retries: int = 0
    retry_count: int = 0


@dataclass
class Workflow:
    id: str
    title: str
    category: str = "general"
    estimated_time: str = ""
    when_to_use: str = ""
    stages: List[WorkflowStage] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    status: StageStatus = StageStatus.PENDING


# =============================================================================
# Markdown Parser
# =============================================================================
class WorkflowParser:
    """Parse markdown workflow definitions into executable Workflow objects."""

    YAML_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    HEADER_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
    STAGE_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    CHECKBOX_RE = re.compile(r"^-\s+\[([ x])\]\s*(.+)$", re.MULTILINE)
    METADATA_RE = re.compile(r"^([a-z_]+):\s*(.+)$", re.MULTILINE)

    def parse_file(self, path: str) -> Optional[Workflow]:
        text = Path(path).read_text(encoding="utf-8")
        return self.parse_text(text)

    def parse_text(self, text: str) -> Optional[Workflow]:
        wf_id = hashlib.sha256(text.encode()).hexdigest()[:12]
        # Extract YAML frontmatter
        yaml_match = self.YAML_RE.search(text)
        meta: Dict[str, str] = {}
        body = text
        if yaml_match:
            yaml_block = yaml_match.group(1)
            for m in self.METADATA_RE.findall(yaml_block):
                meta[m[0].strip()] = m[1].strip()
            body = text[yaml_match.end():]
        # Parse title
        headers = self.HEADER_RE.findall(body)
        title = headers[0] if headers else "Untitled Workflow"
        # Parse stages from ## headers
        stages: List[WorkflowStage] = []
        stage_matches = list(self.STAGE_RE.finditer(body))
        for i, match in enumerate(stage_matches):
            stage_name = match.group(1).strip()
            start = match.end()
            end = stage_matches[i + 1].start() if i + 1 < len(stage_matches) else len(body)
            stage_body = body[start:end]
            # Extract checkboxes as sub-tasks
            checkboxes = self.CHECKBOX_RE.findall(stage_body)
            stage = WorkflowStage(
                name=stage_name,
                description=stage_body.strip()[:200],
                agent=meta.get("default_agent", ""),
            )
            if checkboxes:
                stage.outputs["checklist"] = [{"done": c[0] == "x", "text": c[1]} for c in checkboxes]
            stages.append(stage)
        return Workflow(
            id=wf_id,
            title=title,
            category=meta.get("category", "general"),
            estimated_time=meta.get("estimated_time", ""),
            when_to_use=meta.get("when_to_use", ""),
            stages=stages,
        )


# =============================================================================
# Condition Evaluator
# =============================================================================
class ConditionEvaluator:
    """Evaluate simple conditions like 'hour >= 9', 'day == Monday'."""

    def __init__(self, context: Dict[str, Any]) -> None:
        self.context = context

    def evaluate(self, condition: str) -> bool:
        if not condition:
            return True
        # Simple parser: left op right
        ops = {
            "==": lambda a, b: str(a) == str(b),
            "!=": lambda a, b: str(a) != str(b),
            ">=": lambda a, b: float(a) >= float(b),
            "<=": lambda a, b: float(a) <= float(b),
            ">": lambda a, b: float(a) > float(b),
            "<": lambda a, b: float(a) < float(b),
            "in": lambda a, b: str(a) in str(b),
        }
        for op_str, op_fn in ops.items():
            if op_str in condition:
                parts = condition.split(op_str, 1)
                if len(parts) == 2:
                    left = self._resolve(parts[0].strip())
                    right = self._resolve(parts[1].strip())
                    try:
                        return op_fn(left, right)
                    except Exception:
                        return False
        # Default: treat as truthy check
        return bool(self._resolve(condition.strip()))

    def _resolve(self, expr: str) -> Any:
        expr = expr.strip().strip('"').strip("'")
        if expr in self.context:
            return self.context[expr]
        try:
            return int(expr)
        except ValueError:
            try:
                return float(expr)
            except ValueError:
                return expr


# =============================================================================
# Stage Executor
# =============================================================================
class StageExecutor(ABC):
    @abstractmethod
    def execute(self, stage: WorkflowStage, workflow: Workflow) -> bool: ...


class DefaultStageExecutor(StageExecutor):
    """Default executor that marks stages complete after simulated work."""

    def __init__(self, hooks: Optional[Dict[str, Callable[[WorkflowStage, Workflow], bool]]] = None) -> None:
        self.hooks = hooks or {}

    def execute(self, stage: WorkflowStage, workflow: Workflow) -> bool:
        hook = self.hooks.get(stage.name) or self.hooks.get(stage.agent)
        if hook:
            return hook(stage, workflow)
        # Simulate work
        time.sleep(0.01)
        return True


# =============================================================================
# Workflow Engine
# =============================================================================
class WorkflowEngine:
    """Parse, store, and execute markdown-defined workflows."""

    def __init__(self, workflow_dir: str = WORKFLOW_DIR) -> None:
        self.workflow_dir = Path(workflow_dir)
        self.workflow_dir.mkdir(parents=True, exist_ok=True)
        self._workflows: Dict[str, Workflow] = {}
        self._parser = WorkflowParser()
        self._executor: StageExecutor = DefaultStageExecutor()
        self._context: Dict[str, Any] = {
            "hour": time.localtime().tm_hour,
            "day": time.strftime("%A"),
            "date": time.strftime("%Y-%m-%d"),
        }
        self._lock = threading.Lock()
        self._history: List[Dict[str, Any]] = []
        self._on_stage_complete: List[Callable[[WorkflowStage, Workflow], None]] = []
        self._on_workflow_complete: List[Callable[[Workflow], None]] = []
        self._load_all()

    def _load_all(self) -> None:
        for p in self.workflow_dir.glob("*.md"):
            wf = self._parser.parse_file(str(p))
            if wf:
                self._workflows[wf.id] = wf

    def register_executor(self, executor: StageExecutor) -> None:
        self._executor = executor

    def on_stage_complete(self, callback: Callable[[WorkflowStage, Workflow], None]) -> None:
        self._on_stage_complete.append(callback)

    def on_workflow_complete(self, callback: Callable[[Workflow], None]) -> None:
        self._on_workflow_complete.append(callback)

    def create_workflow(self, markdown: str) -> Optional[Workflow]:
        wf = self._parser.parse_text(markdown)
        if wf:
            self._workflows[wf.id] = wf
            # Save to disk
            safe_title = re.sub(r"[^\w-]", "_", wf.title.lower())[:40]
            path = self.workflow_dir / f"{safe_title}.md"
            path.write_text(markdown, encoding="utf-8")
        return wf

    def get_workflow(self, wf_id: str) -> Optional[Workflow]:
        return self._workflows.get(wf_id)

    def list_workflows(self, category: Optional[str] = None) -> List[Workflow]:
        wfs = list(self._workflows.values())
        if category:
            wfs = [w for w in wfs if w.category == category]
        return wfs

    def run(self, wf_id: str, inputs: Optional[Dict[str, Any]] = None) -> Workflow:
        wf = self._workflows.get(wf_id)
        if not wf:
            raise ValueError(f"Workflow {wf_id} not found")
        wf.inputs.update(inputs or {})
        wf.status = StageStatus.RUNNING
        evaluator = ConditionEvaluator({**self._context, **wf.inputs})
        for stage in wf.stages:
            stage.status = StageStatus.RUNNING
            stage.started_at = time.time()
            # Check condition
            if stage.condition and not evaluator.evaluate(stage.condition):
                stage.status = StageStatus.SKIPPED
                stage.completed_at = time.time()
                continue
            # Execute with retries
            success = False
            for attempt in range(stage.retries + 1):
                success = self._executor.execute(stage, wf)
                if success:
                    break
                stage.retry_count += 1
            stage.completed_at = time.time()
            stage.duration_ms = (stage.completed_at - stage.started_at) * 1000 if stage.started_at else 0
            stage.status = StageStatus.COMPLETED if success else StageStatus.FAILED
            for cb in self._on_stage_complete:
                cb(stage, wf)
            if not success:
                wf.status = StageStatus.FAILED
                break
        else:
            wf.status = StageStatus.COMPLETED
        for cb in self._on_workflow_complete:
            cb(wf)
        with self._lock:
            self._history.append({
                "workflow_id": wf.id,
                "title": wf.title,
                "status": wf.status.value,
                "completed_at": time.time(),
                "stages": [{"name": s.name, "status": s.status.value, "duration_ms": s.duration_ms} for s in wf.stages],
            })
        return wf

    def run_async(self, wf_id: str, inputs: Optional[Dict[str, Any]] = None) -> threading.Thread:
        def _run() -> None:
            self.run(wf_id, inputs)
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history)[-limit:]

    def export_report(self, wf_id: str) -> str:
        wf = self._workflows.get(wf_id)
        if not wf:
            return ""
        lines = [f"# Workflow Report: {wf.title}", f"Category: {wf.category}", f"Status: {wf.status.value}", ""]
        for stage in wf.stages:
            icon = "✓" if stage.status == StageStatus.COMPLETED else "✗" if stage.status == StageStatus.FAILED else "→"
            lines.append(f"## {icon} {stage.name}")
            lines.append(f"Duration: {stage.duration_ms:.1f}ms | Status: {stage.status.value}")
            if stage.outputs:
                lines.append(f"Outputs: {json.dumps(stage.outputs, indent=2)}")
            lines.append("")
        return "\n".join(lines)


# =============================================================================
# Workflow Kernel Bridge
# =============================================================================
class WorkflowKernelBridge:
    def __init__(self, engine: WorkflowEngine, event_bus: Any = None) -> None:
        self.engine = engine
        self.bus = event_bus
        engine.on_stage_complete(self._on_stage)
        engine.on_workflow_complete(self._on_workflow)

    def _on_stage(self, stage: WorkflowStage, workflow: Workflow) -> None:
        if self.bus:
            self.bus.publish("workflow.stage_completed", {
                "workflow_id": workflow.id,
                "stage": stage.name,
                "status": stage.status.value,
            })

    def _on_workflow(self, workflow: Workflow) -> None:
        if self.bus:
            self.bus.publish("workflow.completed", {
                "workflow_id": workflow.id,
                "title": workflow.title,
                "status": workflow.status.value,
            })


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Workflow Engine Demo")
    print("=" * 60)
    engine = WorkflowEngine("/tmp/magnatrix_demo_workflows")
    md = """---
category: daily
estimated_time: 5 min
when_to_use: Start of day
---
# Daily Standup

## Pick Focus
- [ ] Review goals from GOALS.md
- [ ] Identify top 3 priorities
- [ ] Block calendar time

## Process Backlog
- [ ] Scan Tasks/ for blocked items
- [ ] Re-prioritize if needed

## Wrap Up
- [ ] Log decisions to Knowledge/
"""
    wf = engine.create_workflow(md)
    if wf:
        print(f"Created workflow: {wf.title} ({len(wf.stages)} stages)")
        result = engine.run(wf.id)
        print(f"Run complete: {result.status.value}")
        print(engine.export_report(wf.id))
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
