"""DNA Aligner — Needleman-Wunsch, Smith-Waterman, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class DNAAligner:
    def __init__(self, match: int = 1, mismatch: int = -1, gap: int = -2):
        self.match = match
        self.mismatch = mismatch
        self.gap = gap

    def _score(self, a: str, b: str) -> int:
        return self.match if a == b else self.mismatch

    def needleman_wunsch(self, seq1: str, seq2: str) -> Tuple[str, str, int]:
        m, n = len(seq1), len(seq2)
        score = [[0]*(n+1) for _ in range(m+1)]
        for i in range(m+1):
            score[i][0] = self.gap * i
        for j in range(n+1):
            score[0][j] = self.gap * j
        for i in range(1, m+1):
            for j in range(1, n+1):
                match = score[i-1][j-1] + self._score(seq1[i-1], seq2[j-1])
                delete = score[i-1][j] + self.gap
                insert = score[i][j-1] + self.gap
                score[i][j] = max(match, delete, insert)
        align1, align2 = "", ""
        i, j = m, n
        while i > 0 or j > 0:
            if i > 0 and j > 0 and score[i][j] == score[i-1][j-1] + self._score(seq1[i-1], seq2[j-1]):
                align1 = seq1[i-1] + align1
                align2 = seq2[j-1] + align2
                i -= 1; j -= 1
            elif i > 0 and score[i][j] == score[i-1][j] + self.gap:
                align1 = seq1[i-1] + align1
                align2 = "-" + align2
                i -= 1
            else:
                align1 = "-" + align1
                align2 = seq2[j-1] + align2
                j -= 1
        return align1, align2, score[m][n]

    def smith_waterman(self, seq1: str, seq2: str) -> Tuple[str, str, int]:
        m, n = len(seq1), len(seq2)
        score = [[0]*(n+1) for _ in range(m+1)]
        max_score = 0
        max_i, max_j = 0, 0
        for i in range(1, m+1):
            for j in range(1, n+1):
                match = score[i-1][j-1] + self._score(seq1[i-1], seq2[j-1])
                delete = score[i-1][j] + self.gap
                insert = score[i][j-1] + self.gap
                score[i][j] = max(0, match, delete, insert)
                if score[i][j] > max_score:
                    max_score = score[i][j]
                    max_i, max_j = i, j
        align1, align2 = "", ""
        i, j = max_i, max_j
        while score[i][j] > 0:
            if i > 0 and j > 0 and score[i][j] == score[i-1][j-1] + self._score(seq1[i-1], seq2[j-1]):
                align1 = seq1[i-1] + align1
                align2 = seq2[j-1] + align2
                i -= 1; j -= 1
            elif i > 0 and score[i][j] == score[i-1][j] + self.gap:
                align1 = seq1[i-1] + align1
                align2 = "-" + align2
                i -= 1
            else:
                align1 = "-" + align1
                align2 = seq2[j-1] + align2
                j -= 1
        return align1, align2, max_score

    def stats(self) -> Dict:
        return {"match": self.match, "mismatch": self.mismatch, "gap": self.gap}

def run():
    aligner = DNAAligner(1, -1, -2)
    a1, a2, score = aligner.needleman_wunsch("GATTACA", "GCATGCU")
    print("NW:", a1, a2, score)
    a1, a2, score = aligner.smith_waterman("GATTACA", "GCATGCU")
    print("SW:", a1, a2, score)
    print(aligner.stats())

if __name__ == "__main__":
    run()
