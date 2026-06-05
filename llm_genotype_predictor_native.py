"""Genotype Predictor."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

@dataclass
class GenotypePredictor:
    def punnett(self, p1: str, p2: str) -> Dict[str, float]:
        g1, g2 = [p1[0], p1[1]], [p2[0], p2[1]]
        off = {}
        for a in g1:
            for b in g2:
                gt = "".join(sorted([a, b]))
                off[gt] = off.get(gt, 0) + 0.25
        return off
    def hw(self, p: float) -> Dict[str, float]:
        q = 1 - p
        return {"AA": p*p, "Aa": 2*p*q, "aa": q*q}
    def stats(self, p1: str, p2: str) -> Dict:
        return {"punnett": self.punnett(p1, p2)}

def run():
    gp = GenotypePredictor()
    print(gp.punnett("Aa", "Aa"))
    print(gp.hw(0.7))

if __name__ == "__main__":
    run()
