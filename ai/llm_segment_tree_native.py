"""Segment Tree - Range query for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class SegmentTree:
    data: List[float] = field(default_factory=list)
    tree: List[float] = field(default_factory=list)
    n: int = 0

    def build(self, arr: List[float]) -> None:
        self.data = arr[:]; self.n = len(arr); self.tree = [0.0]*(4*self.n)
        self._build(0, 0, self.n-1)

    def _build(self, node: int, l: int, r: int) -> None:
        if l == r: self.tree[node] = self.data[l]
        else:
            mid = (l+r)//2
            self._build(2*node+1, l, mid); self._build(2*node+2, mid+1, r)
            self.tree[node] = self.tree[2*node+1] + self.tree[2*node+2]

    def query(self, ql: int, qr: int) -> float:
        return self._query(0, 0, self.n-1, ql, qr)

    def _query(self, node: int, l: int, r: int, ql: int, qr: int) -> float:
        if ql > r or qr < l: return 0.0
        if ql <= l and r <= qr: return self.tree[node]
        mid = (l+r)//2
        return self._query(2*node+1, l, mid, ql, qr) + self._query(2*node+2, mid+1, r, ql, qr)

    def stats(self) -> dict:
        return {"size": self.n, "tree_nodes": len(self.tree)}

def run():
    st = SegmentTree()
    st.build([1,2,3,4,5])
    print("Sum 1-3:", st.query(1,3))
    print("Stats:", st.stats())

if __name__ == "__main__": run()
