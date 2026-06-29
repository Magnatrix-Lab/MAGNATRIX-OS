"""
forgetting_decay_engine_native.py
MAGNATRIX-OS — Forgetting & Decay Engine

Inspired by Agent Memory Techniques: Exponential decay and importance-based forgetting. Pure stdlib.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class DecayMemory:
    memory_id: str
    content: str
    importance: float
    created_at: str
    last_accessed: str
    access_count: int = 0
    retention_score: float = 1.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_accessed:
            self.last_accessed = self.created_at


class ForgettingDecayEngine:
    """Exponential decay and importance-based forgetting."""

    def __init__(self, cache_dir: str = "./forgetting_decay", decay_constant: float = 0.05):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.decay_constant = decay_constant
        self.memories: Dict[str, DecayMemory] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "memories.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for mid, md in data.items():
                        self.memories[mid] = DecayMemory(**md)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "memories.json", "w", encoding="utf-8") as f:
            json.dump({mid: asdict(m) for mid, m in self.memories.items()}, f, indent=2)

    def add(self, memory_id: str, content: str, importance: float = 1.0) -> DecayMemory:
        memory = DecayMemory(
            memory_id=memory_id, content=content, importance=importance,
            created_at=datetime.now().isoformat(), last_accessed=datetime.now().isoformat(),
        )
        self.memories[memory_id] = memory
        self._calculate_retention()
        self._save()
        return memory

    def access(self, memory_id: str) -> Optional[DecayMemory]:
        memory = self.memories.get(memory_id)
        if memory:
            memory.access_count += 1
            memory.last_accessed = datetime.now().isoformat()
            memory.retention_score = min(1.0, memory.retention_score + 0.1)
            self._save()
        return memory

    def _calculate_retention(self) -> None:
        now = datetime.now()
        for memory in self.memories.values():
            try:
                created = datetime.fromisoformat(memory.created_at)
                hours_old = (now - created).total_seconds() / 3600
                # Ebbinghaus forgetting curve: R = e^(-t/S) where S is stability
                stability = memory.importance * 10 + memory.access_count * 2
                retention = math.exp(-hours_old / max(1, stability))
                memory.retention_score = round(retention, 4)
            except ValueError:
                pass

    def prune(self, threshold: float = 0.1) -> int:
        """Remove memories with retention below threshold."""
        self._calculate_retention()
        to_remove = [mid for mid, m in self.memories.items() if m.retention_score < threshold]
        for mid in to_remove:
            del self.memories[mid]
        self._save()
        return len(to_remove)

    def get_retained(self, min_retention: float = 0.3) -> List[DecayMemory]:
        self._calculate_retention()
        return [m for m in self.memories.values() if m.retention_score >= min_retention]

    def get_stats(self) -> Dict[str, Any]:
        self._calculate_retention()
        avg_retention = sum(m.retention_score for m in self.memories.values()) / max(1, len(self.memories))
        return {"total_memories": len(self.memories), "avg_retention": round(avg_retention, 4)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ForgettingDecayEngine", "DecayMemory"]