"""Mutation Tracker."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Variant:
    chrom: str
    pos: int
    ref: str
    alt: str
    qual: float = 0.0

class MutationTracker:
    def __init__(self):
        self.variants: List[Variant] = []
    def add(self, v: Variant):
        self.variants.append(v)
    def snp_count(self) -> int:
        return sum(1 for v in self.variants if len(v.ref) == 1 and len(v.alt) == 1)
    def indel_count(self) -> int:
        return sum(1 for v in self.variants if len(v.ref) != len(v.alt))
    def ti_tv(self) -> float:
        ti = sum(1 for v in self.variants if (v.ref, v.alt) in [("A","G"),("G","A"),("C","T"),("T","C")])
        tv = self.snp_count() - ti
        return ti / tv if tv > 0 else 0.0
    def by_chrom(self) -> Dict[str, int]:
        c = {}
        for v in self.variants:
            c[v.chrom] = c.get(v.chrom, 0) + 1
        return c
    def stats(self) -> Dict:
        return {"variants": len(self.variants), "snps": self.snp_count(), "indels": self.indel_count(), "ti_tv": round(self.ti_tv(), 2)}

def run():
    mt = MutationTracker()
    mt.add(Variant("1", 1000, "A", "G", 40))
    mt.add(Variant("1", 2000, "C", "CT", 35))
    print(mt.stats())

if __name__ == "__main__":
    run()
