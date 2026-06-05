"""Sequence Assembler — overlap graph, greedy assembly, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto

class SequenceAssembler:
    def __init__(self, k: int = 3):
        self.k = k
        self.reads: List[str] = []
        self.overlaps: Dict[Tuple[int, int], int] = {}

    def add_read(self, read: str):
        self.reads.append(read)

    def _overlap(self, a: str, b: str) -> int:
        max_ov = 0
        for i in range(1, min(len(a), len(b)) + 1):
            if a[-i:] == b[:i]:
                max_ov = i
        return max_ov

    def build_overlap_graph(self):
        self.overlaps = {}
        for i in range(len(self.reads)):
            for j in range(len(self.reads)):
                if i != j:
                    self.overlaps[(i, j)] = self._overlap(self.reads[i], self.reads[j])

    def greedy_assemble(self) -> str:
        if not self.reads:
            return ""
        self.build_overlap_graph()
        used = set()
        current = 0
        result = self.reads[0]
        used.add(0)
        while len(used) < len(self.reads):
            best_next = None
            best_ov = 0
            for j in range(len(self.reads)):
                if j not in used and self.overlaps.get((current, j), 0) > best_ov:
                    best_ov = self.overlaps[(current, j)]
                    best_next = j
            if best_next is None:
                break
            result += self.reads[best_next][best_ov:]
            used.add(best_next)
            current = best_next
        return result

    def stats(self) -> Dict:
        return {"reads": len(self.reads), "k": self.k, "overlaps": len(self.overlaps)}

def run():
    asm = SequenceAssembler(3)
    asm.add_read("ATCG")
    asm.add_read("CGGT")
    asm.add_read("GTAA")
    asm.add_read("AATC")
    print("Assembly:", asm.greedy_assemble())
    print(asm.stats())

if __name__ == "__main__":
    run()
