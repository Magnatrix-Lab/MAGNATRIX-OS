
"""
multi_agent_memory_sync_native.py
MAGNATRIX-OS — Multi-Agent Memory Sync

Inspired by Memanto multi-agent ecosystem:
Connect memories across Claude Code, Cursor, Codex, Windsurf,
Cline, Continue, Goose, GitHub Copilot, and more.

Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class AgentProfile:
    agent_id: str
    name: str
    agent_type: str  # claude, cursor, codex, windsurf, etc.
    capabilities: List[str] = field(default_factory=list)
    memory_namespace: str = ""
    connected_at: str = ""
    last_active: str = ""
    is_active: bool = True

    def __post_init__(self):
        if not self.connected_at:
            self.connected_at = datetime.now().isoformat()
        if not self.last_active:
            self.last_active = self.connected_at


@dataclass
class MemorySync:
    sync_id: str
    source_agent: str
    target_agent: str
    memory_ids: List[str]
    synced_at: str
    sync_type: str = "push"  # push, pull, bidirectional


class MultiAgentMemorySync:
    """Synchronize memories across multiple AI agents."""

    def __init__(self, sync_dir: str = "./agent_sync"):
        self.sync_dir = Path(sync_dir)
        self.sync_dir.mkdir(exist_ok=True)
        self.agents: Dict[str, AgentProfile] = {}
        self.sync_history: List[MemorySync] = []
        self._load_agents()

    def _load_agents(self) -> None:
        agents_file = self.sync_dir / "agents.json"
        if agents_file.exists():
            try:
                with open(agents_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for aid, ad in data.items():
                        self.agents[aid] = AgentProfile(**ad)
            except Exception:
                pass

    def _save_agents(self) -> None:
        agents_file = self.sync_dir / "agents.json"
        with open(agents_file, "w", encoding="utf-8") as f:
            json.dump({aid: asdict(a) for aid, a in self.agents.items()}, f, indent=2)

    def connect_agent(self, agent_id: str, name: str, agent_type: str,
                      capabilities: Optional[List[str]] = None) -> AgentProfile:
        """Register a new agent for memory sync."""
        profile = AgentProfile(
            agent_id=agent_id, name=name, agent_type=agent_type,
            capabilities=capabilities or [],
            memory_namespace=f"agent_{agent_id}",
        )
        self.agents[agent_id] = profile
        self._save_agents()
        return profile

    def disconnect_agent(self, agent_id: str) -> bool:
        if agent_id in self.agents:
            self.agents[agent_id].is_active = False
            self._save_agents()
            return True
        return False

    def sync_memory(self, memory_id: str, source_agent: str, target_agents: List[str],
                    sync_type: str = "push") -> List[MemorySync]:
        """Sync a memory from source agent to target agents."""
        syncs = []
        for target in target_agents:
            if target not in self.agents or not self.agents[target].is_active:
                continue
            sync = MemorySync(
                sync_id=f"sync_{int(datetime.now().timestamp())}_{source_agent}_{target}",
                source_agent=source_agent, target_agent=target,
                memory_ids=[memory_id], synced_at=datetime.now().isoformat(),
                sync_type=sync_type,
            )
            self.sync_history.append(sync)
            syncs.append(sync)
        self._save_sync_history()
        return syncs

    def sync_batch(self, memory_ids: List[str], source_agent: str, target_agents: List[str]) -> List[MemorySync]:
        """Batch sync multiple memories."""
        all_syncs = []
        for mid in memory_ids:
            syncs = self.sync_memory(mid, source_agent, target_agents)
            all_syncs.extend(syncs)
        return all_syncs

    def _save_sync_history(self) -> None:
        history_file = self.sync_dir / "sync_history.json"
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in self.sync_history[-1000:]], f, indent=2)

    def get_agent_memories(self, agent_id: str) -> List[str]:
        """Get memory IDs associated with an agent."""
        return [s.memory_ids[0] for s in self.sync_history if s.target_agent == agent_id or s.source_agent == agent_id]

    def get_sync_stats(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        if agent_id:
            sent = len([s for s in self.sync_history if s.source_agent == agent_id])
            received = len([s for s in self.sync_history if s.target_agent == agent_id])
            return {"sent": sent, "received": received, "total": sent + received}
        return {
            "total_syncs": len(self.sync_history),
            "active_agents": len([a for a in self.agents.values() if a.is_active]),
            "total_agents": len(self.agents),
        }

    def get_compatible_agents(self, agent_type: str) -> List[AgentProfile]:
        """Get agents compatible with a given agent type."""
        return [a for a in self.agents.values() if a.is_active and a.agent_type != agent_type]

    def get_namespace(self, agent_id: str) -> str:
        if agent_id in self.agents:
            return self.agents[agent_id].memory_namespace
        return f"agent_{agent_id}"

    def to_dict(self) -> Dict[str, Any]:
        return self.get_sync_stats()


__all__ = ["MultiAgentMemorySync", "AgentProfile", "MemorySync"]
