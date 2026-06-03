"""LLM Agent Coordinator — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class AgentStatus(Enum):
    IDLE = auto()
    BUSY = auto()
    OFFLINE = auto()
    ERROR = auto()

@dataclass
class Agent:
    id: str
    name: str
    capabilities: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    task_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class AgentCoordinator:
    def __init__(self) -> None:
        self._agents: Dict[str, Agent] = {}
        self._task_queue: List[tuple] = []

    def register(self, agent: Agent) -> None:
        self._agents[agent.id] = agent

    def unregister(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    def assign_task(self, task_id: str, required_capabilities: List[str]) -> Optional[Agent]:
        candidates = []
        for agent in self._agents.values():
            if agent.status == AgentStatus.IDLE and all(c in agent.capabilities for c in required_capabilities):
                candidates.append(agent)
        if not candidates:
            return None
        selected = min(candidates, key=lambda a: a.task_count)
        selected.status = AgentStatus.BUSY
        selected.task_count += 1
        return selected

    def release_agent(self, agent_id: str) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = AgentStatus.IDLE

    def get_available(self) -> List[Agent]:
        return [a for a in self._agents.values() if a.status == AgentStatus.IDLE]

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for a in self._agents.values():
            counts[a.status.name] = counts.get(a.status.name, 0) + 1
        return {"agents": len(self._agents), "by_status": counts, "total_tasks": sum(a.task_count for a in self._agents.values())}

def run() -> None:
    print("Agent Coordinator test")
    e = AgentCoordinator()
    e.register(Agent("a1", "Researcher", ["search", "summarize"]))
    e.register(Agent("a2", "Coder", ["code", "debug"]))
    e.register(Agent("a3", "Writer", ["write", "edit"]))
    agent = e.assign_task("t1", ["search"])
    print("  Assigned to: " + (agent.name if agent else "None"))
    agent2 = e.assign_task("t2", ["search"])
    print("  Assigned to: " + (agent2.name if agent2 else "None"))
    e.release_agent("a1")
    print("  Available after release: " + str(len(e.get_available())))
    print("  Stats: " + str(e.get_stats()))
    print("Agent Coordinator test complete.")

if __name__ == "__main__":
    run()
