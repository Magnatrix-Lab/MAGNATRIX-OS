"""
mcp_a2a_bridge_native.py
MAGNATRIX-OS — MCP/A2A Bridge

Inspired by OmniRoute: MCP (Model Context Protocol) and A2A (Agent-to-Agent) bridge. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class MCPMessage:
    message_id: str
    sender: str
    recipient: str
    action: str
    payload: Dict[str, Any]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MCPA2ABridge:
    """Bridge for MCP and A2A protocol messaging between agents."""

    SUPPORTED_ACTIONS = ["query", "execute", "delegate", "respond", "notify", "sync"]

    def __init__(self, cache_dir: str = "./mcp_a2a"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.messages: List[MCPMessage] = []
        self.agents: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "messages.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.messages = [MCPMessage(**m) for m in data]
            except Exception:
                pass
        agents = self.cache_dir / "agents.json"
        if agents.exists():
            try:
                with open(agents, "r", encoding="utf-8") as f:
                    self.agents = json.load(f)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "messages.json", "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self.messages], f, indent=2)
        with open(self.cache_dir / "agents.json", "w", encoding="utf-8") as f:
            json.dump(self.agents, f, indent=2)

    def register_agent(self, agent_id: str, capabilities: List[str], endpoint: str) -> None:
        self.agents[agent_id] = {"capabilities": capabilities, "endpoint": endpoint, "registered_at": datetime.now().isoformat()}
        self._save()

    def send(self, message_id: str, sender: str, recipient: str, action: str, payload: Dict[str, Any]) -> MCPMessage:
        msg = MCPMessage(message_id=message_id, sender=sender, recipient=recipient, action=action, payload=payload)
        self.messages.append(msg)
        self._save()
        return msg

    def query(self, agent_id: str, query: str) -> Dict[str, Any]:
        """Query an agent's capabilities."""
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        return {"agent_id": agent_id, "capabilities": agent.get("capabilities", []), "query": query}

    def delegate(self, task_id: str, from_agent: str, to_agent: str, task: Dict[str, Any]) -> MCPMessage:
        return self.send(f"delegate_{task_id}", from_agent, to_agent, "delegate", task)

    def get_inbox(self, agent_id: str) -> List[MCPMessage]:
        return [m for m in self.messages if m.recipient == agent_id]

    def get_stats(self) -> Dict[str, Any]:
        return {"messages": len(self.messages), "agents": len(self.agents)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MCPA2ABridge", "MCPMessage"]