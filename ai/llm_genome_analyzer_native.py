"""Genome Analyzer - GC content, ORF for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class GenomeAnalyzer:

    def gc_content(self, seq: str) -> float:
        gc = sum(1 for c in seq.upper() if c in "GC")
        return gc / len(seq) if seq else 0.0

    def find_orfs(self, seq: str, min_len: int = 6) -> List[Tuple[int, int]]:
        orfs = []
        for i in range(len(seq)-min_len+1):
            if seq[i:i+3] == "ATG":
                for j in range(i+3, len(seq), 3):
                    if seq[j:j+3] in ["TAA", "TAG", "TGA"]:
                        if j+3-i >= min_len: orfs.append((i, j+3))
                        break
        return orfs

    def nucleotide_freq(self, seq: str) -> Dict[str, float]:
        counts = {"A": 0, "T": 0, "G": 0, "C": 0}
        for c in seq.upper():
            if c in counts: counts[c] += 1
        return {k: round(v/len(seq), 4) for k, v in counts.items()} if seq else counts

    def stats(self, seq: str) -> dict:
        return {"length": len(seq), "gc": round(self.gc_content(seq), 4), "orfs": len(self.find_orfs(seq))}

def run():
    ga = GenomeAnalyzer()
    seq = "ATGCGATGCGATGCTAA"
    print("GC:", round(ga.gc_content(seq), 4))
    print("ORFs:", ga.find_orfs(seq))
    print("Stats:", ga.stats(seq))

if __name__ == "__main__": run()
