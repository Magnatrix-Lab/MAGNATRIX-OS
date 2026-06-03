"""LLM Text Diff Engine — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class DiffType(Enum):
    EQUAL = auto()
    INSERT = auto()
    DELETE = auto()
    REPLACE = auto()

@dataclass
class DiffBlock:
    diff_type: DiffType
    old_text: str
    new_text: str
    old_start: int = 0
    new_start: int = 0

class TextDiffEngine:
    def __init__(self) -> None:
        pass

    def diff(self, old_text: str, new_text: str) -> List[DiffBlock]:
        old_lines = old_text.splitlines() if old_text else []
        new_lines = new_text.splitlines() if new_text else []
        m, n = len(old_lines), len(new_lines)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m - 1, -1, -1):
            for j in range(n - 1, -1, -1):
                if old_lines[i] == new_lines[j]:
                    dp[i][j] = 1 + dp[i + 1][j + 1]
                else:
                    dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
        i, j = 0, 0
        blocks = []
        while i < m or j < n:
            if i < m and j < n and old_lines[i] == new_lines[j]:
                equal_start = i
                while i < m and j < n and old_lines[i] == new_lines[j]:
                    i += 1
                    j += 1
                blocks.append(DiffBlock(DiffType.EQUAL, "\n".join(old_lines[equal_start:i]), "\n".join(new_lines[equal_start:j]), equal_start, equal_start))
            elif j < n and (i >= m or dp[i][j + 1] >= dp[i + 1][j]):
                insert_start = j
                j += 1
                blocks.append(DiffBlock(DiffType.INSERT, "", new_lines[insert_start], i, insert_start))
            elif i < m:
                delete_start = i
                i += 1
                blocks.append(DiffBlock(DiffType.DELETE, old_lines[delete_start], "", delete_start, j))
            else:
                break
        return blocks

    def patch(self, old_text: str, blocks: List[DiffBlock]) -> str:
        result = []
        for block in blocks:
            if block.diff_type in (DiffType.EQUAL, DiffType.INSERT):
                if block.new_text:
                    result.append(block.new_text)
        return "\n".join(result)

    def unified_diff(self, old_text: str, new_text: str, context: int = 3) -> str:
        blocks = self.diff(old_text, new_text)
        lines = []
        for block in blocks:
            if block.diff_type == DiffType.EQUAL:
                for line in block.new_text.splitlines():
                    lines.append(" " + line)
            elif block.diff_type == DiffType.INSERT:
                for line in block.new_text.splitlines():
                    lines.append("+" + line)
            elif block.diff_type == DiffType.DELETE:
                for line in block.old_text.splitlines():
                    lines.append("-" + line)
        return "\n".join(lines)

    def get_stats(self, blocks: List[DiffBlock]) -> Dict[str, Any]:
        counts = {}
        for b in blocks:
            counts[b.diff_type.name] = counts.get(b.diff_type.name, 0) + 1
        return {"blocks": len(blocks), "by_type": counts, "insertions": sum(len(b.new_text) for b in blocks if b.diff_type == DiffType.INSERT), "deletions": sum(len(b.old_text) for b in blocks if b.diff_type == DiffType.DELETE)}

def run() -> None:
    print("Text Diff Engine test")
    e = TextDiffEngine()
    old = "line1\nline2\nline3\nline4"
    new = "line1\nline2 modified\nline3\nline5"
    blocks = e.diff(old, new)
    for b in blocks:
        print("  " + b.diff_type.name + ": old='" + b.old_text + "' new='" + b.new_text + "'")
    print("  Unified:\n" + e.unified_diff(old, new))
    print("  Stats: " + str(e.get_stats(blocks)))
    print("Text Diff Engine test complete.")

if __name__ == "__main__":
    run()
