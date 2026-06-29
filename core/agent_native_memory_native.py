"""
agent_native_memory_native.py
MAGNATRIX-OS — Agent-Native Memory

Inspired by arXiv 2606.24775: Agent-native memory system with representation, extraction, retrieval, maintenance. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class MemoryEntry:
    entry_id: str
    content: str
    memory_type: str  # episodic, semantic, procedural
    importance: float
    timestamp: str
    access_count: int = 0


class AgentNativeMemory:
    """Agent-native memory with representation, extraction, retrieval, maintenance."""

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

    def store(self, entry_id: str, content: str, memory_type: str, importance: float, timestamp: str) -> MemoryEntry:
        entry = MemoryEntry(entry_id=entry_id, content=content, memory_type=memory_type, importance=importance, timestamp=timestamp)
        self.entries[entry_id] = entry
        self._save()
        return entry

    def retrieve(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """Simple keyword-based retrieval."""
        q = query.lower()
        scored = []
        for entry in self.entries.values():
            score = 0
            if q in entry.content.lower():
                score += 1.0
            if entry.memory_type in q:
                score += 0.5
            score += entry.importance * 0.3
            score += entry.access_count * 0.01
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    def consolidate(self, threshold: float = 0.5) -> int:
        """Remove low-importance memories."""
        removed = [eid for eid, e in self.entries.items() if e.importance < threshold]
        for eid in removed:
            del self.entries[eid]
        self._save()
        return len(removed)

    def get_stats(self) -> Dict[str, Any]:
        types = {}
        for e in self.entries.values():
            types[e.memory_type] = types.get(e.memory_type, 0) + 1
        return {"total_entries": len(self.entries), "types": types}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AgentNativeMemory", "MemoryEntry"]