"""Fenwick Tree - BIT for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass
class FenwickTree:
    n: int = 0
    tree: List[float] = field(default_factory=list)

    def build(self, arr: List[float]) -> None:
        self.n = len(arr); self.tree = [0.0]*(self.n+1)
        for i in range(self.n): self.update(i, arr[i])

    def update(self, idx: int, delta: float) -> None:
        i = idx + 1
        while i <= self.n: self.tree[i] += delta; i += i & -i

    def query(self, idx: int) -> float:
        i = idx + 1; res = 0.0
        while i > 0: res += self.tree[i]; i -= i & -i
        return res

    def range_query(self, l: int, r: int) -> float:
        return self.query(r) - self.query(l-1) if l > 0 else self.query(r)

    def stats(self) -> dict:
        return {"size": self.n, "sum": self.query(self.n-1)}

def run():
    ft = FenwickTree()
    ft.build([1,2,3,4,5])
    print("Prefix 3:", ft.query(3))
    print("Range 1-3:", ft.range_query(1,3))
    print("Stats:", ft.stats())

if __name__ == "__main__": run()
