
"""
memory_conflict_resolver_native.py
MAGNATRIX-OS — Memory Conflict Resolver

Inspired by Memanto conflict detection:
Detect contradictions, explicit versioning, no silent overwrites.
Daily intelligence workflows with summaries and conflict resolution.

Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto


class ConflictResolution(Enum):
    KEEP_LATEST = auto()
    KEEP_OLDEST = auto()
    MERGE = auto()
    MANUAL = auto()
    REJECT_BOTH = auto()
    KEEP_HIGHER_CONFIDENCE = auto()


@dataclass
class MemoryConflict:
    conflict_id: str
    memory_ids: List[str]
    conflicting_contents: List[str]
    conflict_type: str  # "contradiction", "duplicate", "outdated", "ambiguous"
    detected_at: str
    resolution: Optional[str] = None
    resolution_strategy: Optional[str] = None
    resolved_at: Optional[str] = None


class MemoryConflictResolver:
    """Detect and resolve memory conflicts intelligently."""

    def __init__(self, conflicts_file: str = "memory_conflicts.json"):
        self.conflicts_file = Path(conflicts_file)
        self.conflicts_file.parent.mkdir(parents=True, exist_ok=True)
        self.conflicts: List[MemoryConflict] = []
        self._load()

    def _load(self) -> None:
        if self.conflicts_file.exists():
            try:
                with open(self.conflicts_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cd in data:
                        self.conflicts.append(MemoryConflict(**cd))
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.conflicts_file, "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in self.conflicts], f, indent=2)

    def detect_contradictions(self, memories: List[Dict[str, Any]]) -> List[MemoryConflict]:
        """Detect contradictions among memory entries."""
        new_conflicts = []
        # Group by similar content
        content_map = {}
        for m in memories:
            # Use first 5 words as key
            key = " ".join(m.get("content", "").lower().split()[:5])
            content_map.setdefault(key, []).append(m)
        # Check for contradictions within groups
        for key, group in content_map.items():
            if len(group) < 2:
                continue
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    m1, m2 = group[i], group[j]
                    # Check if they contradict (low word overlap)
                    words1 = set(m1.get("content", "").lower().split())
                    words2 = set(m2.get("content", "").lower().split())
                    overlap = len(words1 & words2) / max(len(words1), len(words2), 1)
                    if overlap < 0.5 and m1.get("memory_type") == m2.get("memory_type"):
                        conflict = MemoryConflict(
                            conflict_id=f"conflict_{m1.get('memory_id', 'unknown')}_{m2.get('memory_id', 'unknown')}",
                            memory_ids=[m1.get("memory_id", ""), m2.get("memory_id", "")],
                            conflicting_contents=[m1.get("content", ""), m2.get("content", "")],
                            conflict_type="contradiction",
                            detected_at=datetime.now().isoformat(),
                        )
                        new_conflicts.append(conflict)
                        self.conflicts.append(conflict)
        self._save()
        return new_conflicts

    def detect_duplicates(self, memories: List[Dict[str, Any]]) -> List[MemoryConflict]:
        """Detect near-duplicate memories."""
        new_conflicts = []
        seen = {}
        for m in memories:
            content = m.get("content", "").lower().strip()
            if content in seen:
                conflict = MemoryConflict(
                    conflict_id=f"dup_{m.get('memory_id', 'unknown')}_{seen[content]}",
                    memory_ids=[m.get("memory_id", ""), seen[content]],
                    conflicting_contents=[content, content],
                    conflict_type="duplicate",
                    detected_at=datetime.now().isoformat(),
                )
                new_conflicts.append(conflict)
                self.conflicts.append(conflict)
            else:
                seen[content] = m.get("memory_id", "")
        self._save()
        return new_conflicts

    def resolve(self, conflict_id: str, strategy: ConflictResolution,
                chosen_content: Optional[str] = None) -> Optional[MemoryConflict]:
        """Resolve a conflict with a chosen strategy."""
        for c in self.conflicts:
            if c.conflict_id == conflict_id:
                c.resolution_strategy = strategy.name
                if chosen_content:
                    c.resolution = chosen_content
                elif strategy == ConflictResolution.KEEP_LATEST:
                    c.resolution = c.conflicting_contents[-1] if c.conflicting_contents else None
                elif strategy == ConflictResolution.KEEP_OLDEST:
                    c.resolution = c.conflicting_contents[0] if c.conflicting_contents else None
                elif strategy == ConflictResolution.MERGE:
                    c.resolution = " | ".join(c.conflicting_contents)
                elif strategy == ConflictResolution.REJECT_BOTH:
                    c.resolution = "REJECTED"
                c.resolved_at = datetime.now().isoformat()
                self._save()
                return c
        return None

    def daily_summary(self) -> Dict[str, Any]:
        """Generate daily conflict summary."""
        today = datetime.now().strftime("%Y-%m-%d")
        today_conflicts = [c for c in self.conflicts if c.detected_at.startswith(today)]
        resolved_today = [c for c in today_conflicts if c.resolved_at and c.resolved_at.startswith(today)]
        return {
            "date": today,
            "new_conflicts": len(today_conflicts),
            "resolved": len(resolved_today),
            "pending": len(today_conflicts) - len(resolved_today),
            "by_type": self._breakdown_by_type(today_conflicts),
        }

    def _breakdown_by_type(self, conflicts: List[MemoryConflict]) -> Dict[str, int]:
        counts = {}
        for c in conflicts:
            counts[c.conflict_type] = counts.get(c.conflict_type, 0) + 1
        return counts

    def get_pending(self) -> List[MemoryConflict]:
        return [c for c in self.conflicts if not c.resolution]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.conflicts)
        resolved = sum(1 for c in self.conflicts if c.resolution)
        return {
            "total_conflicts": total,
            "resolved": resolved,
            "pending": total - resolved,
            "by_type": self._breakdown_by_type(self.conflicts),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MemoryConflictResolver", "MemoryConflict", "ConflictResolution"]
