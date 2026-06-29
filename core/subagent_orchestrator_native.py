"""
subagent_orchestrator_native.py
MAGNATRIX-OS — Subagent Orchestrator

Inspired by Deer-Flow (ByteDance): Subagent orchestration with message gateway.
Spawn, coordinate, and manage subagents with inter-agent messaging. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Subagent:
    subagent_id: str
    name: str
    role: str
    parent_id: str
    status: str = "idle"  # idle, running, completed, failed
    capabilities: List[str] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class SubagentMessage:
    msg_id: str
    from_id: str
    to_id: str
    content: str
    msg_type: str = "task"  # task, result, query, notify
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class SubagentOrchestrator:
    """Spawn, coordinate, and manage subagents with inter-agent messaging."""

    def __init__(self, orchestrator_dir: str = "./subagents"):
        self.orchestrator_dir = Path(orchestrator_dir)
        self.orchestrator_dir.mkdir(exist_ok=True)
        self.subagents: Dict[str, Subagent] = {}
        self.messages: List[SubagentMessage] = []
        self._load()

    def _load(self) -> None:
        file = self.orchestrator_dir / "subagents.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        self.subagents[sid] = Subagent(**sd)
            except Exception:
                pass
        file2 = self.orchestrator_dir / "messages.json"
        if file2.exists():
            try:
                with open(file2, "r", encoding="utf-8") as f:
                    self.messages = [SubagentMessage(**m) for m in json.load(f)]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.orchestrator_dir / "subagents.json", "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self.subagents.items()}, f, indent=2)
        with open(self.orchestrator_dir / "messages.json", "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self.messages[-500:]], f, indent=2)

    def spawn(self, subagent_id: str, name: str, role: str, parent_id: str,
              capabilities: Optional[List[str]] = None) -> Subagent:
        subagent = Subagent(
            subagent_id=subagent_id, name=name, role=role, parent_id=parent_id,
            capabilities=capabilities or [],
        )
        self.subagents[subagent_id] = subagent
        self._save()
        return subagent

    def dispatch(self, subagent_id: str, task: str) -> bool:
        subagent = self.subagents.get(subagent_id)
        if not subagent or subagent.status == "running":
            return False
        subagent.status = "running"
        msg = SubagentMessage(
            msg_id=f"{subagent_id}_{len(self.messages)}", from_id=subagent.parent_id,
            to_id=subagent_id, content=task, msg_type="task",
        )
        subagent.messages.append(asdict(msg))
        self.messages.append(msg)
        self._save()
        return True

    def report(self, subagent_id: str, result: str) -> bool:
        subagent = self.subagents.get(subagent_id)
        if not subagent or subagent.status != "running":
            return False
        subagent.status = "completed"
        msg = SubagentMessage(
            msg_id=f"{subagent_id}_{len(self.messages)}", from_id=subagent_id,
            to_id=subagent.parent_id, content=result, msg_type="result",
        )
        subagent.messages.append(asdict(msg))
        self.messages.append(msg)
        self._save()
        return True

    def fail(self, subagent_id: str, error: str) -> bool:
        subagent = self.subagents.get(subagent_id)
        if not subagent:
            return False
        subagent.status = "failed"
        msg = SubagentMessage(
            msg_id=f"{subagent_id}_{len(self.messages)}", from_id=subagent_id,
            to_id=subagent.parent_id, content=error, msg_type="notify",
        )
        subagent.messages.append(asdict(msg))
        self.messages.append(msg)
        self._save()
        return True

    def get_subagent(self, subagent_id: str) -> Optional[Subagent]:
        return self.subagents.get(subagent_id)

    def get_subagents(self, parent_id: Optional[str] = None) -> List[Subagent]:
        if parent_id:
            return [s for s in self.subagents.values() if s.parent_id == parent_id]
        return list(self.subagents.values())

    def get_inbox(self, subagent_id: str) -> List[SubagentMessage]:
        return [m for m in self.messages if m.to_id == subagent_id]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.subagents)
        running = sum(1 for s in self.subagents.values() if s.status == "running")
        completed = sum(1 for s in self.subagents.values() if s.status == "completed")
        failed = sum(1 for s in self.subagents.values() if s.status == "failed")
        return {"subagents": total, "running": running, "completed": completed, "failed": failed, "messages": len(self.messages)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SubagentOrchestrator", "Subagent", "SubagentMessage"]