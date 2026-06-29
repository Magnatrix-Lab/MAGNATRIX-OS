"""
redteam_operation_planner_native.py
MAGNATRIX-OS — Red Team Operation Planner

Inspired by AbyssSec red team methodology:
Plan and track red team operations with phases, objectives, and opsec. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class OperationPhase:
    phase_id: str
    name: str
    objectives: List[str] = field(default_factory=list)
    status: str = "pending"
    opsec_level: str = "high"  # low, medium, high


@dataclass
class RedTeamOperation:
    operation_id: str
    codename: str
    target_scope: str
    phases: List[OperationPhase] = field(default_factory=list)
    status: str = "planning"
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class RedTeamOperationPlanner:
    """Plan and track red team operations with phases, objectives, and opsec."""

    def __init__(self, planner_dir: str = "./redteam_ops"):
        self.planner_dir = Path(planner_dir)
        self.planner_dir.mkdir(exist_ok=True)
        self.operations: Dict[str, RedTeamOperation] = {}
        self._load()

    def _load(self) -> None:
        file = self.planner_dir / "operations.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for oid, od in data.items():
                        od["phases"] = [OperationPhase(**p) for p in od.get("phases", [])]
                        self.operations[oid] = RedTeamOperation(**od)
            except Exception:
                pass

    def _save(self) -> None:
        out = {}
        for oid, o in self.operations.items():
            d = asdict(o)
            d["phases"] = [asdict(p) for p in o.phases]
            out[oid] = d
        with open(self.planner_dir / "operations.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def create_operation(self, operation_id: str, codename: str, target_scope: str) -> RedTeamOperation:
        op = RedTeamOperation(operation_id=operation_id, codename=codename, target_scope=target_scope)
        self.operations[operation_id] = op
        self._save()
        return op

    def add_phase(self, operation_id: str, phase_id: str, name: str, objectives: List[str],
                  opsec_level: str = "high") -> bool:
        op = self.operations.get(operation_id)
        if not op:
            return False
        phase = OperationPhase(phase_id=phase_id, name=name, objectives=objectives, opsec_level=opsec_level)
        op.phases.append(phase)
        self._save()
        return True

    def start_phase(self, operation_id: str, phase_id: str) -> bool:
        op = self.operations.get(operation_id)
        if not op:
            return False
        for p in op.phases:
            if p.phase_id == phase_id:
                p.status = "active"
                op.status = "active"
                self._save()
                return True
        return False

    def complete_phase(self, operation_id: str, phase_id: str) -> bool:
        op = self.operations.get(operation_id)
        if not op:
            return False
        for p in op.phases:
            if p.phase_id == phase_id:
                p.status = "completed"
                if all(ph.status == "completed" for ph in op.phases):
                    op.status = "completed"
                self._save()
                return True
        return False

    def get_operation(self, operation_id: str) -> Optional[RedTeamOperation]:
        return self.operations.get(operation_id)

    def list_operations(self) -> List[RedTeamOperation]:
        return list(self.operations.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.operations)
        active = sum(1 for o in self.operations.values() if o.status == "active")
        completed = sum(1 for o in self.operations.values() if o.status == "completed")
        return {"operations": total, "active": active, "completed": completed}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["RedTeamOperationPlanner", "RedTeamOperation", "OperationPhase"]