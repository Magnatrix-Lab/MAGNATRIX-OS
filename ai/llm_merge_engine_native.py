"""
llm_merge_engine_native.py
MAGNATRIX-OS Merge Engine
Native Python, stdlib only.
Provides three-way merge, conflict detection, auto-resolution strategies, and merge commit tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class ConflictResolution(Enum):
    BASE = "base"
    OURS = "ours"
    THEIRS = "theirs"
    MANUAL = "manual"


@dataclass
class Conflict:
    path: str
    base_value: Any
    ours_value: Any
    theirs_value: Any
    resolution: ConflictResolution = ConflictResolution.MANUAL
    resolved_value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path, "base": self.base_value, "ours": self.ours_value,
            "theirs": self.theirs_value, "resolution": self.resolution.value,
            "resolved": self.resolved_value,
        }


@dataclass
class MergeResult:
    success: bool
    merged: Dict[str, Any]
    conflicts: List[Conflict]
    conflict_count: int
    auto_resolved: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success, "conflicts": [c.to_dict() for c in self.conflicts],
            "conflict_count": self.conflict_count, "auto_resolved": self.auto_resolved,
        }


class MergeEngine:
    """Three-way merge engine with conflict detection and resolution."""

    def __init__(self, default_strategy: ConflictResolution = ConflictResolution.MANUAL) -> None:
        self.default_strategy = default_strategy

    def merge(self, base: Dict[str, Any], ours: Dict[str, Any], theirs: Dict[str, Any],
              strategy: Optional[ConflictResolution] = None) -> MergeResult:
        strategy = strategy or self.default_strategy
        merged = dict(base)
        conflicts = []
        auto_resolved = 0

        all_keys = set(base.keys()) | set(ours.keys()) | set(theirs.keys())

        for key in all_keys:
            b = base.get(key)
            o = ours.get(key)
            t = theirs.get(key)

            if o == t:
                if o is not None:
                    merged[key] = o
            elif o == b:
                if t is not None:
                    merged[key] = t
            elif t == b:
                if o is not None:
                    merged[key] = o
            else:
                # All three differ
                conflict = Conflict(path=key, base_value=b, ours_value=o, theirs_value=t)
                if strategy == ConflictResolution.OURS:
                    conflict.resolution = ConflictResolution.OURS
                    conflict.resolved_value = o
                    merged[key] = o
                    auto_resolved += 1
                elif strategy == ConflictResolution.THEIRS:
                    conflict.resolution = ConflictResolution.THEIRS
                    conflict.resolved_value = t
                    merged[key] = t
                    auto_resolved += 1
                elif strategy == ConflictResolution.BASE:
                    conflict.resolution = ConflictResolution.BASE
                    conflict.resolved_value = b
                    merged[key] = b
                    auto_resolved += 1
                else:
                    conflicts.append(conflict)

        return MergeResult(
            success=len(conflicts) == 0,
            merged=merged,
            conflicts=conflicts,
            conflict_count=len(conflicts),
            auto_resolved=auto_resolved
        )

    def resolve_conflict(self, conflict: Conflict, resolution: ConflictResolution, value: Any) -> None:
        conflict.resolution = resolution
        conflict.resolved_value = value

    def apply_resolutions(self, merged: Dict[str, Any], conflicts: List[Conflict]) -> Dict[str, Any]:
        result = dict(merged)
        for c in conflicts:
            if c.resolved_value is not None:
                keys = c.path.split(".")
                current = result
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                current[keys[-1]] = c.resolved_value
        return result

    def text_merge(self, base_lines: List[str], ours_lines: List[str], theirs_lines: List[str]) -> Tuple[List[str], List[Conflict]]:
        conflicts = []
        merged = []
        max_len = max(len(base_lines), len(ours_lines), len(theirs_lines))
        for i in range(max_len):
            b = base_lines[i] if i < len(base_lines) else None
            o = ours_lines[i] if i < len(ours_lines) else None
            t = theirs_lines[i] if i < len(theirs_lines) else None

            if o == t:
                merged.append(o or "")
            elif o == b:
                merged.append(t or "")
            elif t == b:
                merged.append(o or "")
            else:
                conflicts.append(Conflict(path=f"line_{i}", base_value=b, ours_value=o, theirs_value=t))
                merged.append(f"<<<<<<< ours\n{o}\n=======\n{t}\n>>>>>>> theirs")
        return merged, conflicts


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Merge Engine")
    print("=" * 60)

    engine = MergeEngine()

    base = {"name": "config", "version": 1, "theme": "dark", "debug": False}
    ours = {"name": "config", "version": 2, "theme": "dark", "debug": True}
    theirs = {"name": "config", "version": 2, "theme": "light", "debug": False}

    print("\n--- Manual strategy ---")
    result = engine.merge(base, ours, theirs, ConflictResolution.MANUAL)
    print(f"  Success: {result.success}")
    print(f"  Conflicts: {result.conflict_count}")
    for c in result.conflicts:
        print(f"    {c.path}: ours={c.ours_value}, theirs={c.theirs_value}")

    print("\n--- Ours strategy ---")
    result = engine.merge(base, ours, theirs, ConflictResolution.OURS)
    print(f"  Success: {result.success}")
    print(f"  Merged: {result.merged}")

    print("\n--- Text merge ---")
    base_text = ["line1", "line2", "line3"]
    ours_text = ["line1", "line2 modified", "line3"]
    theirs_text = ["line1", "line2", "line3 added"]
    merged, conflicts = engine.text_merge(base_text, ours_text, theirs_text)
    for line in merged:
        print(f"  {line}")
    print(f"  Conflicts: {len(conflicts)}")

    print("\nMerge Engine test complete.")


if __name__ == "__main__":
    run()
