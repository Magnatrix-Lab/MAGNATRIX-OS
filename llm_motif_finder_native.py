"""Motif Finder — consensus, PWM, entropy, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class MotifFinder:
    sequences: List[str] = field(default_factory=list)
    pwm: Dict[str, List[float]] = field(default_factory=dict)

    def build_pwm(self, aligned: List[str]) -> Dict[str, List[float]]:
        if not aligned:
            return {}
        width = len(aligned[0])
        counts = {b: [0]*width for b in "ACGT"}
        for seq in aligned:
            for i, b in enumerate(seq):
                if b in counts:
                    counts[b][i] += 1
        total = len(aligned)
        self.pwm = {b: [(c + 0.5) / (total + 2) for c in counts[b]] for b in counts}
        return self.pwm

    def consensus(self, aligned: List[str]) -> str:
        if not aligned:
            return ""
        pwm = self.build_pwm(aligned)
        width = len(aligned[0])
        return ''.join(max("ACGT", key=lambda b: pwm[b][i]) for i in range(width))

    def score(self, seq: str) -> float:
        if not self.pwm or len(seq) != len(next(iter(self.pwm.values()))):
            return 0.0
        score = 0.0
        for i, b in enumerate(seq):
            if b in self.pwm:
                score += math.log2(self.pwm[b][i] / 0.25)
        return score

    def information_content(self) -> List[float]:
        if not self.pwm:
            return []
        width = len(next(iter(self.pwm.values())))
        ic = []
        for i in range(width):
            e = 0.0
            for b in "ACGT":
                p = self.pwm[b][i]
                if p > 0:
                    e += p * math.log2(p / 0.25)
            ic.append(e)
        return ic

    def stats(self) -> Dict:
        return {"sequences": len(self.sequences), "pwm_width": len(next(iter(self.pwm.values()))) if self.pwm else 0}

def run():
    mf = MotifFinder(sequences=["ATGCG", "ATGCG", "ATGCG"])
    print("Consensus:", mf.consensus(["ATGCG", "ATGCG", "ATGCG"]))
    print("Score:", mf.score("ATGCG"))
    print("IC:", mf.information_content())
    print(mf.stats())

if __name__ == "__main__":
    run()
