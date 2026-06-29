"""Squad Role Dispatcher — Assign manager/worker/inspector roles."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class RoleAssignment:
    agent_id: str = ""
    role: str = ""
    assigned_at: float = 0.0
    assigned_by: str = ""
    tasks: list[str] = None

    def __post_init__(self):
        if self.tasks is None:
            self.tasks = []

class SquadRoleDispatcher:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._assignments: dict[str, RoleAssignment] = {}
        self._role_templates: dict[str, dict] = {
            "manager": {"description": "Coordinates tasks, assigns work, reviews output", "permissions": ["assign", "review", "broadcast"]},
            "worker": {"description": "Executes tasks, reports progress, asks for clarification", "permissions": ["execute", "report", "ask"]},
            "inspector": {"description": "Validates output, checks quality, flags issues", "permissions": ["validate", "flag", "approve", "reject"]},
        }
        self._persist_path = self.root / "squad_roles.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._assignments = {k: RoleAssignment(**v) for k, v in data.get("assignments", {}).items()}
            self._role_templates = data.get("templates", self._role_templates)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "assignments": {k: v.__dict__ for k, v in self._assignments.items()},
            "templates": self._role_templates
        }, indent=2))

    def assign(self, agent_id: str, role: str, assigned_by: str = "system") -> RoleAssignment:
        import time
        if role not in self._role_templates:
            self._role_templates[role] = {"description": f"Custom role: {role}", "permissions": ["execute"]}
        assignment = RoleAssignment(agent_id=agent_id, role=role, assigned_at=time.time(), assigned_by=assigned_by)
        self._assignments[agent_id] = assignment
        self._save()
        return assignment

    def get_role(self, agent_id: str) -> str | None:
        a = self._assignments.get(agent_id)
        return a.role if a else None

    def get_permissions(self, role: str) -> list[str]:
        return self._role_templates.get(role, {}).get("permissions", [])

    def add_task(self, agent_id: str, task: str) -> bool:
        a = self._assignments.get(agent_id)
        if a:
            a.tasks.append(task)
            self._save()
            return True
        return False

    def list_by_role(self, role: str) -> list[RoleAssignment]:
        return [a for a in self._assignments.values() if a.role == role]

    def remove(self, agent_id: str) -> bool:
        if agent_id in self._assignments:
            del self._assignments[agent_id]
            self._save()
            return True
        return False

    def to_dict(self) -> dict:
        return {"assignment_count": len(self._assignments), "templates": len(self._role_templates)}

    def get_stats(self) -> dict:
        by_role = {}
        for a in self._assignments.values():
            by_role[a.role] = by_role.get(a.role, 0) + 1
        return {"assignments": len(self._assignments), "by_role": by_role, "templates": len(self._role_templates)}

__all__ = ["SquadRoleDispatcher", "RoleAssignment"]
