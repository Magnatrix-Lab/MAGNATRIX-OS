
"""
hippocampus_memory_native.py
MAGNATRIX-OS — Hippocampus Memory Layer

Inspired by Synapse biological hippocampus layer:
- Salience scoring (amygdala tagging important experiences)
- Forgetting curve (Ebbinghaus exponential decay)
- Memory consolidation during idle time
- Important memories persist, unimportant ones fade

Pure Python standard library.
"""

import math
import time
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class MemoryEntry:
    """A single memory with hippocampus tracking."""
    memory_id: str
    content: str
    created_at: str
    salience: float = 0.5
    access_count: int = 0
    last_accessed: str = ""
    correction_count: int = 0
    emotional_marker: float = 0.0
    consolidation_level: float = 0.0
    forget_at: Optional[str] = None

    def __post_init__(self):
        if not self.last_accessed:
            self.last_accessed = self.created_at


class HippocampusMemoryLayer:
    """Biological memory management with salience and forgetting."""

    # Ebbinghaus forgetting curve parameters
    FORGETTING_BASE = 1.0
    FORGETTING_DECAY_RATE = 0.05
    CONSOLIDATION_THRESHOLD = 0.7
    SALIENCE_IMPORTANCE_BONUS = 0.4

    def __init__(self, memory_file: str = "hippocampus_memory.json"):
        self.memory_file = Path(memory_file)
        self.memories: Dict[str, MemoryEntry] = {}
        self._load()

    def _load(self) -> None:
        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for mid, md in data.items():
                    self.memories[mid] = MemoryEntry(**md)

    def _save(self) -> None:
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump({mid: asdict(m) for mid, m in self.memories.items()}, f, indent=2)

    def add_memory(self, memory_id: str, content: str, salience: float = 0.5,
                   emotional_marker: float = 0.0) -> MemoryEntry:
        now = datetime.now().isoformat()
        entry = MemoryEntry(
            memory_id=memory_id, content=content, created_at=now,
            salience=salience, emotional_marker=emotional_marker,
            last_accessed=now,
        )
        self._update_forget_time(entry)
        self.memories[memory_id] = entry
        self._save()
        return entry

    def _update_forget_time(self, entry: MemoryEntry) -> None:
        # Higher salience = longer retention
        decay_rate = self.FORGETTING_DECAY_RATE / max(entry.salience, 0.1)
        # Important memories decay 4x slower
        if entry.salience > 0.7:
            decay_rate /= 4.0
        # Days until forgotten: base / decay_rate
        retention_days = self.FORGETTING_BASE / decay_rate
        forget_time = datetime.now() + timedelta(days=retention_days)
        entry.forget_at = forget_time.isoformat()

    def access(self, memory_id: str) -> Optional[MemoryEntry]:
        """Access a memory - strengthens it (spacing effect)."""
        if memory_id not in self.memories:
            return None
        entry = self.memories[memory_id]
        entry.access_count += 1
        entry.last_accessed = datetime.now().isoformat()
        # Spacing effect: each access strengthens memory
        entry.consolidation_level = min(1.0, entry.consolidation_level + 0.1)
        self._update_forget_time(entry)
        self._save()
        return entry

    def score_salience(self, memory_id: str) -> float:
        """Score memory importance 0.0-1.0."""
        if memory_id not in self.memories:
            return 0.0
        entry = self.memories[memory_id]
        now = datetime.now()
        created = datetime.fromisoformat(entry.created_at)
        age_hours = (now - created).total_seconds() / 3600
        # Recency: newer = higher
        recency = max(0, 1.0 - (age_hours / 168))  # 1 week decay
        # Frequency: more access = higher
        frequency = min(1.0, entry.access_count / 10.0)
        # Corrections: more corrections = higher (mistakes remembered vividly)
        correction_score = min(1.0, entry.correction_count / 5.0)
        # Emotional marker
        emotional = entry.emotional_marker
        # Weighted combination
        salience = (
            recency * 0.3 +
            frequency * 0.25 +
            correction_score * 0.2 +
            emotional * 0.15 +
            entry.consolidation_level * 0.1
        )
        entry.salience = min(1.0, salience)
        self._save()
        return entry.salience

    def should_forget(self, memory_id: str) -> bool:
        if memory_id not in self.memories:
            return True
        entry = self.memories[memory_id]
        if entry.forget_at is None:
            return False
        return datetime.now() >= datetime.fromisoformat(entry.forget_at)

    def prune_forgotten(self) -> int:
        """Remove memories that have passed their forgetting threshold."""
        to_remove = [mid for mid in self.memories if self.should_forget(mid)]
        for mid in to_remove:
            del self.memories[mid]
        if to_remove:
            self._save()
        return len(to_remove)

    def get_active_memories(self, limit: Optional[int] = None) -> List[MemoryEntry]:
        """Get memories that haven't been forgotten, sorted by salience."""
        active = [m for m in self.memories.values() if not self.should_forget(m.memory_id)]
        active.sort(key=lambda x: x.salience, reverse=True)
        return active[:limit] if limit else active

    def get_by_salience(self, min_salience: float = 0.0) -> List[MemoryEntry]:
        return [m for m in self.memories.values() if m.salience >= min_salience]

    def to_dict(self) -> Dict:
        return {
            "total_memories": len(self.memories),
            "active_memories": len(self.get_active_memories()),
            "avg_salience": sum(m.salience for m in self.memories.values()) / max(len(self.memories), 1),
            "high_salience": len(self.get_by_salience(0.7)),
        }


__all__ = ["HippocampusMemoryLayer", "MemoryEntry"]
