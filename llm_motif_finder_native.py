"""Motif Finder — consensus sequence, profile matrix, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from collections import Counter

class MotifFinder:
    def __init__(self, motif_length: int = 6):
        self.motif_length = motif_length

    def _profile(self, sequences: List[str]) -> Dict[str, List[float]]:
        bases = ["A", "C", "G", "T"]
        profile = {b: [0.0]*self.motif_length for b in bases}
        for seq in sequences:
            for i in range(self.motif_length):
                if i < len(seq) and seq[i] in bases:
                    profile[seq[i]][i] += 1.0 / len(sequences)
        return profile

    def consensus(self, sequences: List[str]) -> str:
        profile = self._profile(sequences)
        result = ""
        for i in range(self.motif_length):
            best = max(profile.keys(), key=lambda b: profile[b][i])
            result += best
        return result

    def score(self, sequences: List[str]) -> int:
        consensus = self.consensus(sequences)
        total = 0
        for seq in sequences:
            for i in range(self.motif_length):
                if i < len(seq) and seq[i] != consensus[i]:
                    total += 1
        return total

    def find_motifs(self, dna: str, k: int = None) -> List[str]:
        k = k or self.motif_length
        return [dna[i:i+k] for i in range(len(dna) - k + 1)]

    def most_common_motif(self, sequences: List[str], k: int = None) -> Tuple[str, int]:
        k = k or self.motif_length
        motifs = []
        for seq in sequences:
            motifs.extend(self.find_motifs(seq, k))
        freq = Counter(motifs)
        return freq.most_common(1)[0] if freq else ("", 0)

    def stats(self) -> Dict:
        return {"motif_length": self.motif_length}

def run():
    finder = MotifFinder(6)
    seqs = ["GATTACA", "GATTAGA", "GATCACA", "GATTACC"]
    print("Consensus:", finder.consensus(seqs))
    print("Score:", finder.score(seqs))
    print("Most common:", finder.most_common_motif(seqs))
    print(finder.stats())

if __name__ == "__main__":
    run()
