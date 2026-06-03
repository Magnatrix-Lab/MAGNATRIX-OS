"""
llm_diff_engine_native.py
MAGNATRIX-OS Diff Engine
Native Python, stdlib only.
Provides text diff, JSON diff, deep object diff, and unified/patch format generation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union


class DiffType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class DiffEntry:
    path: str
    diff_type: DiffType
    old_value: Any = None
    new_value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "type": self.diff_type.value, "old": self.old_value, "new": self.new_value}


class DiffEngine:
    """Unified diff engine for text, JSON, and nested objects."""

    def __init__(self) -> None:
        self._context_lines = 3

    def text_diff(self, old: str, new: str) -> List[str]:
        old_lines = old.splitlines()
        new_lines = new.splitlines()
        return self._lcs_diff(old_lines, new_lines)

    def _lcs_diff(self, old: List[str], new: List[str]) -> List[str]:
        m, n = len(old), len(new)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if old[i - 1] == new[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        result = []
        i, j = m, n
        while i > 0 or j > 0:
            if i > 0 and j > 0 and old[i - 1] == new[j - 1]:
                result.append(f" {old[i - 1]}")
                i -= 1; j -= 1
            elif j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
                result.append(f"+{new[j - 1]}")
                j -= 1
            else:
                result.append(f"-{old[i - 1]}")
                i -= 1
        return list(reversed(result))

    def json_diff(self, old: Dict[str, Any], new: Dict[str, Any], path: str = "") -> List[DiffEntry]:
        diffs = []
        all_keys = set(old.keys()) | set(new.keys())
        for key in sorted(all_keys):
            current_path = f"{path}.{key}" if path else key
            if key not in old:
                diffs.append(DiffEntry(current_path, DiffType.ADDED, None, new[key]))
            elif key not in new:
                diffs.append(DiffEntry(current_path, DiffType.REMOVED, old[key], None))
            elif isinstance(old[key], dict) and isinstance(new[key], dict):
                diffs.extend(self.json_diff(old[key], new[key], current_path))
            elif old[key] != new[key]:
                diffs.append(DiffEntry(current_path, DiffType.MODIFIED, old[key], new[key]))
            else:
                diffs.append(DiffEntry(current_path, DiffType.UNCHANGED, old[key], new[key]))
        return diffs

    def list_diff(self, old: List[Any], new: List[Any]) -> List[DiffEntry]:
        diffs = []
        max_len = max(len(old), len(new))
        for i in range(max_len):
            path = f"[{i}]"
            if i >= len(old):
                diffs.append(DiffEntry(path, DiffType.ADDED, None, new[i]))
            elif i >= len(new):
                diffs.append(DiffEntry(path, DiffType.REMOVED, old[i], None))
            elif old[i] != new[i]:
                diffs.append(DiffEntry(path, DiffType.MODIFIED, old[i], new[i]))
        return diffs

    def unified_format(self, diffs: List[DiffEntry]) -> str:
        lines = []
        for d in diffs:
            if d.diff_type == DiffType.ADDED:
                lines.append(f"+ {d.path}: {d.new_value}")
            elif d.diff_type == DiffType.REMOVED:
                lines.append(f"- {d.path}: {d.old_value}")
            elif d.diff_type == DiffType.MODIFIED:
                lines.append(f"~ {d.path}: {d.old_value} -> {d.new_value}")
        return "\n".join(lines)

    def patch_apply(self, target: Dict[str, Any], diffs: List[DiffEntry]) -> Dict[str, Any]:
        result = dict(target)
        for d in diffs:
            keys = d.path.split(".")
            current = result
            for key in keys[:-1]:
                if key not in current or not isinstance(current[key], dict):
                    current[key] = {}
                current = current[key]
            if d.diff_type == DiffType.ADDED or d.diff_type == DiffType.MODIFIED:
                current[keys[-1]] = d.new_value
            elif d.diff_type == DiffType.REMOVED:
                current.pop(keys[-1], None)
        return result


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Diff Engine")
    print("=" * 60)

    engine = DiffEngine()

    print("\n--- Text diff ---")
    old_text = "line1\nline2\nline3\nline4"
    new_text = "line1\nline2 modified\nline3\nline5"
    diff = engine.text_diff(old_text, new_text)
    for line in diff:
        print(f"  {line}")

    print("\n--- JSON diff ---")
    old_json = {"name": "Alice", "age": 30, "settings": {"theme": "dark"}}
    new_json = {"name": "Alice", "age": 31, "settings": {"theme": "light", "font": "16px"}}
    diffs = engine.json_diff(old_json, new_json)
    for d in diffs:
        if d.diff_type != DiffType.UNCHANGED:
            print(f"  {d.diff_type.value}: {d.path}")

    print("\n--- Unified format ---")
    print(engine.unified_format(diffs))

    print("\n--- Patch apply ---")
    patched = engine.patch_apply(old_json, [d for d in diffs if d.diff_type != DiffType.UNCHANGED])
    print(f"  Patched: {patched}")

    print("\nDiff Engine test complete.")


if __name__ == "__main__":
    run()
