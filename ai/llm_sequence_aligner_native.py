"""Sequence Aligner - Needleman-Wunsch for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class SequenceAligner:
    match: int = 1; mismatch: int = -1; gap: int = -1

    def align(self, seq1: str, seq2: str) -> Tuple[int, str, str]:
        m, n = len(seq1), len(seq2)
        dp = [[0]*(n+1) for _ in range(m+1)]
        for i in range(m+1): dp[i][0] = self.gap * i
        for j in range(n+1): dp[0][j] = self.gap * j
        for i in range(1, m+1):
            for j in range(1, n+1):
                score = self.match if seq1[i-1] == seq2[j-1] else self.mismatch
                dp[i][j] = max(dp[i-1][j-1] + score, dp[i-1][j] + self.gap, dp[i][j-1] + self.gap)
        i, j = m, n
        a1, a2 = [], []
        while i > 0 or j > 0:
            if i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + (self.match if seq1[i-1]==seq2[j-1] else self.mismatch):
                a1.append(seq1[i-1]); a2.append(seq2[j-1]); i -= 1; j -= 1
            elif i > 0 and dp[i][j] == dp[i-1][j] + self.gap:
                a1.append(seq1[i-1]); a2.append("-"); i -= 1
            else:
                a1.append("-"); a2.append(seq2[j-1]); j -= 1
        return dp[m][n], "".join(reversed(a1)), "".join(reversed(a2))

    def stats(self, seq1: str, seq2: str) -> dict:
        score, a1, a2 = self.align(seq1, seq2)
        return {"score": score, "len": len(a1)}

def run():
    sa = SequenceAligner()
    score, a1, a2 = sa.align("GATTACA", "GCATGCU")
    print(f"Score: {score}, A1: {a1}, A2: {a2}")
    print("Stats:", sa.stats("GATTACA", "GCATGCU"))

if __name__ == "__main__": run()
