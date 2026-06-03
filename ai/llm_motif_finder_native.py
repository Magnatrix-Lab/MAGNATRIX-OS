"""Motif Finder - DNA motif detection for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from collections import Counter

@dataclass
class MotifFinder:
    k: int = 3

    def find_kmers(self, sequence: str) -> List[str]:
        return [sequence[i:i+self.k] for i in range(len(sequence)-self.k+1)]

    def most_frequent(self, sequences: List[str]) -> Tuple[str, int]:
        all_kmers = []
        for seq in sequences:
            all_kmers.extend(self.find_kmers(seq))
        counts = Counter(all_kmers)
        if counts: return counts.most_common(1)[0]
        return ("", 0)

    def stats(self, sequences: List[str]) -> dict:
        kmers = []
        for seq in sequences: kmers.extend(self.find_kmers(seq))
        return {"k": self.k, "total_kmers": len(kmers), "unique": len(set(kmers))}

def run():
    mf = MotifFinder(3)
    seqs = ["ATGCGATG", "ATGCGATG", "CGATGCGC"]
    print("Most frequent:", mf.most_frequent(seqs))
    print("Stats:", mf.stats(seqs))

if __name__ == "__main__": run()
