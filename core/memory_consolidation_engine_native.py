"""
memory_consolidation_engine_native.py
MAGNATRIX-OS — Memory Consolidation Engine

Inspired by Agent Memory Techniques: Merge similar memories to reduce redundancy. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class MemoryEntry:
    entry_id: str
    content: str
    memory_type: str
    importance: float
    created_at: str
    access_count: int = 0
    last_accessed: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class MemoryConsolidationEngine:
    """Merge similar memories to reduce redundancy."""

    def __init__(self, cache_dir: str = "./memory_consolidation"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.memories: Dict[str, MemoryEntry] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "memories.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for eid, ed in data.items():
                        self.memories[eid] = MemoryEntry(**ed)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "memories.json", "w", encoding="utf-8") as f:
            json.dump({eid: asdict(m) for eid, m in self.memories.items()}, f, indent=2)

    def _similarity(self, a: str, b: str) -> float:
        words_a = set(re.findall(r'\w+', a.lower()))
        words_b = set(re.findall(r'\w+', b.lower()))
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union

    def add(self, entry_id: str, content: str, memory_type: str, importance: float) -> MemoryEntry:
        entry = MemoryEntry(
            entry_id=entry_id, content=content, memory_type=memory_type, importance=importance,
        )
        self.memories[entry_id] = entry
        self._save()
        return entry

    def consolidate(self, threshold: float = 0.7) -> int:
        """Merge similar memories above threshold."""
        merged = 0
        to_remove = []
        entries = list(self.memories.values())
        for i in range(len(entries)):
            if entries[i].entry_id in to_remove:
                continue
            for j in range(i + 1, len(entries)):
                if entries[j].entry_id in to_remove:
                    continue
                sim = self._similarity(entries[i].content, entries[j].content)
                if sim >= threshold and entries[i].memory_type == entries[j].memory_type:
                    # Merge: keep higher importance, combine content
                    entries[i].content = f"{entries[i].content} | {entries[j].content}"
                    entries[i].importance = max(entries[i].importance, entries[j].importance)
                    entries[i].access_count += entries[j].access_count
                    to_remove.append(entries[j].entry_id)
                    merged += 1
        for eid in to_remove:
            if eid in self.memories:
                del self.memories[eid]
        self._save()
        return merged

    def get_memories(self, memory_type: Optional[str] = None) -> List[MemoryEntry]:
        if memory_type:
            return [m for m in self.memories.values() if m.memory_type == memory_type]
        return list(self.memories.values())

    def get_stats(self) -> Dict[str, Any]:
        return {"total_memories": len(self.memories), "types": list(set(m.memory_type for m in self.memories.values()))}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MemoryConsolidationEngine", "MemoryEntry"]