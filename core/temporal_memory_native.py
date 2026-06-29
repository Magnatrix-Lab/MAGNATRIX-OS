"""
temporal_memory_native.py
MAGNATRIX-OS — Temporal Memory

Inspired by Agent Memory Techniques: Time-aware memory with recency decay and temporal ordering. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta


@dataclass
class TemporalEntry:
    entry_id: str
    content: str
    timestamp: str
    importance: float
    recency_score: float = 1.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class TemporalMemory:
    """Time-aware memory with recency decay."""

    def __init__(self, memory_dir: str = "./temporal_memory", decay_rate: float = 0.1):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.decay_rate = decay_rate
        self.entries: Dict[str, TemporalEntry] = {}
        self._load()

    def _load(self) -> None:
        file = self.memory_dir / "entries.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for eid, ed in data.items():
                        self.entries[eid] = TemporalEntry(**ed)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.memory_dir / "entries.json", "w", encoding="utf-8") as f:
            json.dump({eid: asdict(e) for eid, e in self.entries.items()}, f, indent=2)

    def add(self, entry_id: str, content: str, importance: float = 1.0) -> TemporalEntry:
        entry = TemporalEntry(
            entry_id=entry_id, content=content, importance=importance,
            timestamp=datetime.now().isoformat(), recency_score=1.0,
        )
        self.entries[entry_id] = entry
        self._update_recency()
        self._save()
        return entry

    def _update_recency(self) -> None:
        now = datetime.now()
        for entry in self.entries.values():
            try:
                entry_time = datetime.fromisoformat(entry.timestamp)
                hours_old = (now - entry_time).total_seconds() / 3600
                entry.recency_score = max(0.0, 1.0 - (hours_old * self.decay_rate))
            except ValueError:
                pass

    def get_recent(self, hours: int = 24) -> List[TemporalEntry]:
        self._update_recency()
        cutoff = datetime.now() - timedelta(hours=hours)
        return [e for e in self.entries.values() if datetime.fromisoformat(e.timestamp) > cutoff]

    def get_by_recency(self, top_k: int = 10) -> List[TemporalEntry]:
        self._update_recency()
        sorted_entries = sorted(self.entries.values(), key=lambda x: x.recency_score, reverse=True)
        return sorted_entries[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        self._update_recency()
        avg_recency = sum(e.recency_score for e in self.entries.values()) / max(1, len(self.entries))
        return {"total_entries": len(self.entries), "avg_recency": round(avg_recency, 4)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["TemporalMemory", "TemporalEntry"]