"""
multi_agent_shared_memory_native.py
MAGNATRIX-OS — Multi-Agent Shared Memory

Inspired by Agent Memory Techniques: Shared memory space for multiple agents. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class SharedEntry:
    entry_id: str
    content: str
    author_agent: str
    visibility: List[str]  # agent IDs who can see this
    tags: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MultiAgentSharedMemory:
    """Shared memory space for multiple agents."""

    def __init__(self, memory_dir: str = "./multi_agent_memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.entries: Dict[str, SharedEntry] = {}
        self.agents: List[str] = []
        self._load()

    def _load(self) -> None:
        for fname, attr in [("entries.json", "entries"), ("agents.json", "agents")]:
            f = self.memory_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "entries.json":
                            for eid, ed in data.items():
                                self.entries[eid] = SharedEntry(**ed)
                        else:
                            self.agents = data
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.memory_dir / "entries.json", "w", encoding="utf-8") as f:
            json.dump({eid: asdict(e) for eid, e in self.entries.items()}, f, indent=2)
        with open(self.memory_dir / "agents.json", "w", encoding="utf-8") as f:
            json.dump(self.agents, f, indent=2)

    def register_agent(self, agent_id: str) -> None:
        if agent_id not in self.agents:
            self.agents.append(agent_id)
            self._save()

    def add(self, entry_id: str, content: str, author_agent: str, visibility: Optional[List[str]] = None, tags: Optional[List[str]] = None) -> SharedEntry:
        entry = SharedEntry(
            entry_id=entry_id, content=content, author_agent=author_agent,
            visibility=visibility or self.agents, tags=tags or [],
        )
        self.entries[entry_id] = entry
        self._save()
        return entry

    def get_for_agent(self, agent_id: str) -> List[SharedEntry]:
        return [e for e in self.entries.values() if agent_id in e.visibility or "all" in e.visibility]

    def get_by_tag(self, tag: str) -> List[SharedEntry]:
        return [e for e in self.entries.values() if tag in e.tags]

    def get_stats(self) -> Dict[str, Any]:
        return {"total_entries": len(self.entries), "registered_agents": len(self.agents), "tags": list(set(tag for e in self.entries.values() for tag in e.tags))}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MultiAgentSharedMemory", "SharedEntry"]