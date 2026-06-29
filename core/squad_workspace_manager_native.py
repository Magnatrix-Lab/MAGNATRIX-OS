"""Squad Workspace Manager — Project workspace initialization, context sharing."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class SquadWorkspace:
    workspace_id: str = ""
    name: str = ""
    project_path: str = ""
    agents: list[str] = None
    shared_context: dict = None
    created_at: float = 0.0
    active: bool = True

    def __post_init__(self):
        if self.agents is None:
            self.agents = []
        if self.shared_context is None:
            self.shared_context = {}

class SquadWorkspaceManager:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._workspaces: dict[str, SquadWorkspace] = {}
        self._current_workspace: str = ""
        self._persist_path = self.root / "squad_workspaces.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._workspaces = {k: SquadWorkspace(**v) for k, v in data.get("workspaces", {}).items()}
            self._current_workspace = data.get("current", "")

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "workspaces": {k: v.__dict__ for k, v in self._workspaces.items()},
            "current": self._current_workspace
        }, indent=2))

    def init(self, workspace_id: str, name: str, project_path: str = "") -> SquadWorkspace:
        import time
        ws = SquadWorkspace(
            workspace_id=workspace_id, name=name,
            project_path=project_path or str(self.root),
            created_at=time.time()
        )
        self._workspaces[workspace_id] = ws
        self._current_workspace = workspace_id
        self._save()
        return ws

    def add_agent(self, workspace_id: str, agent_id: str) -> bool:
        ws = self._workspaces.get(workspace_id)
        if ws and agent_id not in ws.agents:
            ws.agents.append(agent_id)
            self._save()
            return True
        return False

    def remove_agent(self, workspace_id: str, agent_id: str) -> bool:
        ws = self._workspaces.get(workspace_id)
        if ws and agent_id in ws.agents:
            ws.agents.remove(agent_id)
            self._save()
            return True
        return False

    def set_context(self, workspace_id: str, key: str, value: str) -> bool:
        ws = self._workspaces.get(workspace_id)
        if ws:
            ws.shared_context[key] = value
            self._save()
            return True
        return False

    def get_context(self, workspace_id: str, key: str) -> str | None:
        ws = self._workspaces.get(workspace_id)
        return ws.shared_context.get(key) if ws else None

    def current(self) -> SquadWorkspace | None:
        return self._workspaces.get(self._current_workspace)

    def switch(self, workspace_id: str) -> bool:
        if workspace_id in self._workspaces:
            self._current_workspace = workspace_id
            self._save()
            return True
        return False

    def to_dict(self) -> dict:
        return {"workspace_count": len(self._workspaces), "current": self._current_workspace}

    def get_stats(self) -> dict:
        total_agents = sum(len(w.agents) for w in self._workspaces.values())
        return {"workspaces": len(self._workspaces), "total_agents": total_agents, "active": sum(1 for w in self._workspaces.values() if w.active)}

__all__ = ["SquadWorkspaceManager", "SquadWorkspace"]
