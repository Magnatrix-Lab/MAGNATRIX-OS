
"""
temporal_memory_query_native.py
MAGNATRIX-OS — Temporal Memory Query Engine

Inspired by Memanto temporal queries:
Versioning, recency signals, temporal queries (--as-of, --changed-since),
conflict detection, and explicit versioning.

Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta


@dataclass
class TemporalMemoryVersion:
    version_id: str
    memory_id: str
    content: str
    changed_at: str
    change_type: str  # "create", "update", "delete"
    previous_version: Optional[str] = None


@dataclass
class MemoryConflict:
    conflict_id: str
    memory_id: str
    versions: List[TemporalMemoryVersion] = field(default_factory=list)
    detected_at: str = ""
    resolution: Optional[str] = None


class TemporalMemoryQueryEngine:
    """Temporal memory queries with versioning and conflict detection."""

    def __init__(self, history_file: str = "memory_history.json"):
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.versions: Dict[str, List[TemporalMemoryVersion]] = {}
        self.conflicts: List[MemoryConflict] = []
        self._load()

    def _load(self) -> None:
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for mid, versions in data.items():
                        self.versions[mid] = [TemporalMemoryVersion(**v) for v in versions]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump({mid: [asdict(v) for v in versions] for mid, versions in self.versions.items()}, f, indent=2)

    def record_version(self, memory_id: str, content: str, change_type: str = "update") -> TemporalMemoryVersion:
        """Record a new version of a memory."""
        version = TemporalMemoryVersion(
            version_id=f"{memory_id}_v{len(self.versions.get(memory_id, [])) + 1}",
            memory_id=memory_id, content=content, changed_at=datetime.now().isoformat(),
            change_type=change_type,
            previous_version=self.versions.get(memory_id, [None])[-1].version_id if self.versions.get(memory_id) else None,
        )
        self.versions.setdefault(memory_id, []).append(version)
        self._save()
        # Check for conflicts
        self._detect_conflicts(memory_id)
        return version

    def query_as_of(self, memory_id: str, timestamp: str) -> Optional[TemporalMemoryVersion]:
        """Query memory state as of a specific time."""
        versions = self.versions.get(memory_id, [])
        if not versions:
            return None
        target_time = datetime.fromisoformat(timestamp)
        latest = None
        for v in versions:
            v_time = datetime.fromisoformat(v.changed_at)
            if v_time <= target_time:
                latest = v
        return latest

    def query_changed_since(self, timestamp: str, memory_type: Optional[str] = None) -> List[TemporalMemoryVersion]:
        """Query all changes since a specific time."""
        target_time = datetime.fromisoformat(timestamp)
        changed = []
        for versions in self.versions.values():
            for v in versions:
                if datetime.fromisoformat(v.changed_at) >= target_time:
                    if memory_type is None or v.memory_id.startswith(memory_type):
                        changed.append(v)
        return sorted(changed, key=lambda v: v.changed_at, reverse=True)

    def get_version_history(self, memory_id: str) -> List[TemporalMemoryVersion]:
        """Get full version history of a memory."""
        return self.versions.get(memory_id, [])

    def _detect_conflicts(self, memory_id: str) -> None:
        """Detect contradictions in memory versions."""
        versions = self.versions.get(memory_id, [])
        if len(versions) < 2:
            return
        # Check for contradictions: content changes that negate previous versions
        latest = versions[-1]
        previous = versions[-2]
        # Simple contradiction detection: if content is very different
        latest_words = set(latest.content.lower().split())
        prev_words = set(previous.content.lower().split())
        overlap = len(latest_words & prev_words) / max(len(latest_words), len(prev_words), 1)
        if overlap < 0.3 and latest.change_type == "update":
            conflict = MemoryConflict(
                conflict_id=f"conflict_{memory_id}_{int(datetime.now().timestamp())}",
                memory_id=memory_id,
                versions=[previous, latest],
                detected_at=datetime.now().isoformat(),
            )
            self.conflicts.append(conflict)

    def get_conflicts(self, memory_id: Optional[str] = None) -> List[MemoryConflict]:
        if memory_id:
            return [c for c in self.conflicts if c.memory_id == memory_id]
        return self.conflicts

    def resolve_conflict(self, conflict_id: str, resolution: str) -> bool:
        for c in self.conflicts:
            if c.conflict_id == conflict_id:
                c.resolution = resolution
                return True
        return False

    def get_recency_signal(self, memory_id: str) -> float:
        """Get recency signal (0.0-1.0) for a memory."""
        versions = self.versions.get(memory_id, [])
        if not versions:
            return 0.0
        latest = versions[-1]
        try:
            days_ago = (datetime.now() - datetime.fromisoformat(latest.changed_at)).days
            return max(0, 1 - days_ago / 365)
        except Exception:
            return 0.5

    def get_stats(self) -> Dict[str, Any]:
        total_versions = sum(len(v) for v in self.versions.values())
        return {
            "total_memories": len(self.versions),
            "total_versions": total_versions,
            "conflicts_detected": len(self.conflicts),
            "unresolved_conflicts": len([c for c in self.conflicts if not c.resolution]),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["TemporalMemoryQueryEngine", "TemporalMemoryVersion", "MemoryConflict"]
