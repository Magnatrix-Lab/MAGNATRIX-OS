"""Diff Engine — line diff, unified diff, patches, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

@dataclass
class DiffLine:
    op: str  # +, -, =
    text: str

class DiffEngine:
    def __init__(self):
        pass

    def _lcs(self, a: List[str], b: List[str]) -> List[Tuple[int, int]]:
        m, n = len(a), len(b)
        dp = [[0]*(n+1) for _ in range(m+1)]
        for i in range(1, m+1):
            for j in range(1, n+1):
                if a[i-1] == b[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        matches = []
        i, j = m, n
        while i > 0 and j > 0:
            if a[i-1] == b[j-1]:
                matches.append((i-1, j-1))
                i -= 1; j -= 1
            elif dp[i-1][j] > dp[i][j-1]:
                i -= 1
            else:
                j -= 1
        return list(reversed(matches))

    def diff(self, old: List[str], new: List[str]) -> List[DiffLine]:
        matches = self._lcs(old, new)
        result = []
        oi, ni = 0, 0
        for mi, mj in matches:
            while oi < mi:
                result.append(DiffLine("-", old[oi]))
                oi += 1
            while ni < mj:
                result.append(DiffLine("+", new[ni]))
                ni += 1
            result.append(DiffLine("=", old[oi]))
            oi += 1; ni += 1
        while oi < len(old):
            result.append(DiffLine("-", old[oi]))
            oi += 1
        while ni < len(new):
            result.append(DiffLine("+", new[ni]))
            ni += 1
        return result

    def unified_diff(self, old: List[str], new: List[str], context: int = 3) -> str:
        diffs = self.diff(old, new)
        lines = []
        for d in diffs:
            if d.op == "+":
                lines.append(f"+{d.text}")
            elif d.op == "-":
                lines.append(f"-{d.text}")
            else:
                lines.append(f" {d.text}")
        return ''.join(lines)

    def stats(self) -> Dict:
        return {}

def run():
    diff = DiffEngine()
    old = ["line1", "line2", "line3", "line4"]
    new = ["line1", "line2a", "line3", "line5"]
    for d in diff.diff(old, new):
        print(f"{d.op} {d.text}")
    print(diff.unified_diff(old, new))
    print(diff.stats())

if __name__ == "__main__":
    run()
