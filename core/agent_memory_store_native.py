"""
agent_memory_store_native.py
MAGNATRIX-OS — Agent Memory Store

Inspired by Deer-Flow (ByteDance): Agent memory system with episodic and semantic storage.
Memory storage with retrieval, summarization, and context window management. Pure stdlib.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class MemoryEntry:
    entry_id: str
    agent_id: str
    content: str
    memory_type: str = "episodic"  # episodic, semantic, procedural
    importance: float = 0.5
    timestamp: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class AgentMemoryStore:
    """Agent memory with episodic and semantic storage, retrieval, and context management."""

    def __init__(self, memory_dir: str = "./agent_memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.entries: Dict[str, MemoryEntry] = {}
        self._load()

    def _load(self) -> None:
        file = self.memory_dir / "entries.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for eid, ed in data.items():
                        self.entries[eid] = MemoryEntry(**ed)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.memory_dir / "entries.json", "w", encoding="utf-8") as f:
            json.dump({eid: asdict(e) for eid, e in self.entries.items()}, f, indent=2)

    def store(self, entry_id: str, agent_id: str, content: str,
              memory_type: str = "episodic", importance: float = 0.5,
              tags: Optional[List[str]] = None) -> MemoryEntry:
        entry = MemoryEntry(
            entry_id=entry_id, agent_id=agent_id, content=content,
            memory_type=memory_type, importance=importance, tags=tags or [],
        )
        self.entries[entry_id] = entry
        self._save()
        return entry

    def _tokenize(self, text: str) -> List[str]:
        return text.lower().split()

    def _similarity(self, a: str, b: str) -> float:
        ta, tb = set(self._tokenize(a)), set(self._tokenize(b))
        inter = len(ta & tb)
        union = len(ta | tb)
        return inter / union if union > 0 else 0.0

    def retrieve(self, agent_id: str, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """Retrieve most relevant memories for an agent."""
        candidates = [e for e in self.entries.values() if e.agent_id == agent_id]
        scored = [(self._similarity(query, e.content) * e.importance, e) for e in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    def summarize(self, agent_id: str, memory_type: Optional[str] = None) -> str:
        """Summarize an agent's memories."""
        entries = [e for e in self.entries.values() if e.agent_id == agent_id]
        if memory_type:
            entries = [e for e in entries if e.memory_type == memory_type]
        if not entries:
            return f"No memories for agent {agent_id}"
        # Simple extractive summary: top 3 important entries
        top = sorted(entries, key=lambda x: x.importance, reverse=True)[:3]
        return "\\n".join(f"- {e.content[:200]}" for e in top)

    def forget(self, agent_id: str, threshold: float = 0.1) -> int:
        """Forget low-importance memories."""
        to_remove = [eid for eid, e in self.entries.items() if e.agent_id == agent_id and e.importance < threshold]
        for eid in to_remove:
            del self.entries[eid]
        self._save()
        return len(to_remove)

    def get_agent_memories(self, agent_id: str) -> List[MemoryEntry]:
        return [e for e in self.entries.values() if e.agent_id == agent_id]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.entries)
        by_type = {}
        for e in self.entries.values():
            by_type[e.memory_type] = by_type.get(e.memory_type, 0) + 1
        agents = len(set(e.agent_id for e in self.entries.values()))
        return {"total_entries": total, "by_type": by_type, "agents": agents}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AgentMemoryStore", "MemoryEntry"]