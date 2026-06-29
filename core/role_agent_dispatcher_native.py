"""
role_agent_dispatcher_native.py
MAGNATRIX-OS — Role Agent Dispatcher

Inspired by gajae-code: Role-based agents (executor, architect, planner, critic). Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class RoleAgent:
    agent_id: str
    role: str  # executor, architect, planner, critic
    status: str
    capabilities: List[str] = field(default_factory=list)
    current_task: str = ""


class RoleAgentDispatcher:
    """Dispatch tasks to role-based agents."""

    ROLES = {
        "executor": {"capabilities": ["code", "test", "debug"]},
        "architect": {"capabilities": ["design", "review", "refactor"]},
        "planner": {"capabilities": ["plan", "estimate", "schedule"]},
        "critic": {"capabilities": ["review", "audit", "feedback"]},
    }

    def __init__(self, cache_dir: str = "./role_agents"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.agents: Dict[str, RoleAgent] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "agents.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for aid, ad in data.items():
                        self.agents[aid] = RoleAgent(**ad)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "agents.json", "w", encoding="utf-8") as f:
            json.dump({aid: asdict(a) for aid, a in self.agents.items()}, f, indent=2)

    def register_agent(self, agent_id: str, role: str) -> RoleAgent:
        caps = self.ROLES.get(role, {}).get("capabilities", [])
        agent = RoleAgent(agent_id=agent_id, role=role, status="idle", capabilities=caps)
        self.agents[agent_id] = agent
        self._save()
        return agent

    def assign_task(self, agent_id: str, task: str) -> bool:
        agent = self.agents.get(agent_id)
        if agent and agent.status == "idle":
            agent.status = "busy"
            agent.current_task = task
            self._save()
            return True
        return False

    def release_agent(self, agent_id: str) -> bool:
        agent = self.agents.get(agent_id)
        if agent:
            agent.status = "idle"
            agent.current_task = ""
            self._save()
            return True
        return False

    def get_agents_by_role(self, role: str) -> List[RoleAgent]:
        return [a for a in self.agents.values() if a.role == role]

    def get_available_agents(self) -> List[RoleAgent]:
        return [a for a in self.agents.values() if a.status == "idle"]

    def get_stats(self) -> Dict[str, Any]:
        by_role = {}
        for a in self.agents.values():
            by_role[a.role] = by_role.get(a.role, 0) + 1
        return {"total_agents": len(self.agents), "by_role": by_role}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["RoleAgentDispatcher", "RoleAgent"]