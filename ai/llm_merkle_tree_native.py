"""Merkle Tree - Hash tree for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import hashlib

@dataclass
class MerkleTree:
    leaves: List[str] = field(default_factory=list)
    layers: List[List[str]] = field(default_factory=list)

    def build(self, data: List[str]) -> None:
        self.leaves = [hashlib.sha256(d.encode()).hexdigest() for d in data]
        self.layers = [self.leaves[:]]
        current = self.leaves[:]
        while len(current) > 1:
            if len(current) % 2 == 1: current.append(current[-1])
            current = [hashlib.sha256((current[i]+current[i+1]).encode()).hexdigest() for i in range(0, len(current), 2)]
            self.layers.append(current)

    def get_root(self) -> Optional[str]:
        return self.layers[-1][0] if self.layers else None

    def stats(self) -> dict:
        return {"leaves": len(self.leaves), "root": self.get_root()[:16] if self.get_root() else None}

def run():
    mt = MerkleTree()
    mt.build(["tx1", "tx2", "tx3", "tx4"])
    print("Root:", mt.get_root()[:16])
    print("Stats:", mt.stats())

if __name__ == "__main__": run()
