"""Genome Assembler."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class GenomeAssembler:
    reads: List[str] = field(default_factory=list)
    k: int = 5
    def kmerize(self, read: str) -> List[str]:
        return [read[i:i+self.k] for i in range(len(read)-self.k+1)]
    def overlap(self, a: str, b: str) -> int:
        for i in range(min(len(a), len(b)), 0, -1):
            if a[-i:] == b[:i]: return i
        return 0
    def build_graph(self) -> Dict[str, List[str]]:
        g = {}
        for r in self.reads:
            for kmer in self.kmerize(r):
                g.setdefault(kmer[:-1], []).append(kmer[1:])
        return g
    def assemble(self) -> str:
        if not self.reads: return ""
        contig = self.reads[0]
        used = {0}
        while len(used) < len(self.reads):
            best, best_o = -1, 0
            for i in range(len(self.reads)):
                if i in used: continue
                o = self.overlap(contig, self.reads[i])
                if o > best_o: best_o, best = o, i
            if best == -1 or best_o == 0: break
            contig += self.reads[best][best_o:]
            used.add(best)
        return contig
    def stats(self) -> Dict:
        return {"reads": len(self.reads), "k": self.k, "graph_nodes": len(self.build_graph())}

def run():
    ga = GenomeAssembler(["ATGCG", "GCGTA", "TACGT", "CGTAA"])
    print(ga.stats())
    print(ga.assemble())

if __name__ == "__main__":
    run()
