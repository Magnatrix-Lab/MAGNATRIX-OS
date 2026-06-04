"""Disjoint Set - Union-Find for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class DisjointSet:
    parent: List[int] = field(default_factory=list)
    rank: List[int] = field(default_factory=list)

    def make_set(self, n: int) -> None:
        self.parent = list(range(n)); self.rank = [0]*n

    def find(self, x: int) -> int:
        if self.parent[x] != x: self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> bool:
        rx, ry = self.find(x), self.find(y)
        if rx == ry: return False
        if self.rank[rx] < self.rank[ry]: rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]: self.rank[rx] += 1
        return True

    def stats(self) -> dict:
        roots = set(self.find(i) for i in range(len(self.parent)))
        return {"sets": len(roots), "elements": len(self.parent)}

def run():
    ds = DisjointSet()
    ds.make_set(5)
    ds.union(0,1); ds.union(1,2); ds.union(3,4)
    print("Sets:", ds.stats())
    print("0-2 same:", ds.find(0) == ds.find(2))

if __name__ == "__main__": run()
