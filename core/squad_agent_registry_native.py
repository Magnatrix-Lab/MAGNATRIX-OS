"""Squad Agent Registry — Multi-AI agent registration, role assignment."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class SquadAgent:
    agent_id: str = ""
    name: str = ""
    role: str = ""  # manager | worker | inspector | custom
    model: str = ""  # claude | gemini | codex | opencode | custom
    status: str = "idle"  # idle | active | busy | offline
    workspace: str = ""
    capabilities: list[str] = None
    created_at: float = 0.0

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []

class SquadAgentRegistry:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._agents: dict[str, SquadAgent] = {}
        self._persist_path = self.root / "squad_agents.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._agents = {k: SquadAgent(**v) for k, v in data.get("agents", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "agents": {k: v.__dict__ for k, v in self._agents.items()}
        }, indent=2))

    def register(self, agent_id: str, name: str, role: str, model: str = "", workspace: str = "", capabilities: list[str] = None) -> SquadAgent:
        import time
        agent = SquadAgent(
            agent_id=agent_id, name=name, role=role, model=model,
            workspace=workspace, capabilities=capabilities or [],
            created_at=time.time()
        )
        self._agents[agent_id] = agent
        self._save()
        return agent

    def get(self, agent_id: str) -> SquadAgent | None:
        return self._agents.get(agent_id)

    def list_by_role(self, role: str) -> list[SquadAgent]:
        return [a for a in self._agents.values() if a.role == role]

    def set_status(self, agent_id: str, status: str) -> bool:
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = status
            self._save()
            return True
        return False

    def remove(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._save()
            return True
        return False

    def to_dict(self) -> dict:
        return {"agent_count": len(self._agents), "roles": list(set(a.role for a in self._agents.values()))}

    def get_stats(self) -> dict:
        by_role = {}
        by_status = {}
        for a in self._agents.values():
            by_role[a.role] = by_role.get(a.role, 0) + 1
            by_status[a.status] = by_status.get(a.status, 0) + 1
        return {"total": len(self._agents), "by_role": by_role, "by_status": by_status}

__all__ = ["SquadAgentRegistry", "SquadAgent"]
