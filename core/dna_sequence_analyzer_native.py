#!/usr/bin/env python3
"""DNA Sequence Analyzer for MAGNATRIX-OS."""
from __future__ import annotations
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

class FASTAParser:
    def parse(self, content: str) -> List[Dict[str, str]]:
        sequences = []
        current = {"header": "", "sequence": ""}
        for line in content.strip().split("\n"):
            if line.startswith(">"):
                if current["sequence"]:
                    sequences.append(current.copy())
                current = {"header": line[1:].strip(), "sequence": ""}
            else:
                current["sequence"] += line.strip().upper()
        if current["sequence"]:
            sequences.append(current)
        return sequences

class SequenceAligner:
    def align(self, seq1: str, seq2: str) -> Dict[str, Any]:
        m, n = len(seq1), len(seq2)
        dp = [[0]*(n+1) for _ in range(m+1)]
        for i in range(1, m+1):
            for j in range(1, n+1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        return {"score": dp[m][n], "seq1_len": m, "seq2_len": n}

class MotifFinder:
    def find_motifs(self, sequence: str, pattern: str) -> List[int]:
        positions = []
        regex = pattern.replace("N", "[ATCG]")
        for m in re.finditer(regex, sequence):
            positions.append(m.start())
        return positions

class DNASequenceAnalyzer:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.parser = FASTAParser()
        self.aligner = SequenceAligner()
        self.motif = MotifFinder()
    def analyze(self, fasta_content: str) -> Dict[str, Any]:
        sequences = self.parser.parse(fasta_content)
        stats = []
        for seq in sequences:
            s = seq["sequence"]
            gc = (s.count("G") + s.count("C")) / len(s) * 100 if s else 0
            stats.append({"header": seq["header"], "length": len(s), "gc_content": round(gc, 2)})
        return {"sequences": len(sequences), "stats": stats}
    def to_dict(self):
        return {"parser": "FASTA", "aligner": "LCS", "motif": "regex"}
