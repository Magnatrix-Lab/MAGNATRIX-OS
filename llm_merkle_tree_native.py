"""Merkle Tree — hashing, proof generation, verification, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import hashlib

class MerkleTree:
    def __init__(self, hash_fn: str = "sha256"):
        self.leaves: List[str] = []
        self.layers: List[List[str]] = []
        self.root: str = ""

    def _hash(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    def add_leaf(self, data: str):
        self.leaves.append(self._hash(data))

    def build(self) -> str:
        if not self.leaves:
            return ""
        self.layers = [self.leaves[:]]
        current = self.leaves[:]
        while len(current) > 1:
            next_layer = []
            for i in range(0, len(current), 2):
                left = current[i]
                right = current[i + 1] if i + 1 < len(current) else left
                next_layer.append(self._hash(left + right))
            current = next_layer
            self.layers.append(current)
        self.root = current[0] if current else ""
        return self.root

    def get_proof(self, leaf_index: int) -> List[Tuple[str, str]]:
        proof = []
        idx = leaf_index
        for layer in self.layers[:-1]:
            sibling_idx = idx + 1 if idx % 2 == 0 else idx - 1
            if sibling_idx < len(layer):
                direction = "right" if idx % 2 == 0 else "left"
                proof.append((direction, layer[sibling_idx]))
            idx //= 2
        return proof

    def verify(self, leaf_data: str, proof: List[Tuple[str, str]], root: str) -> bool:
        current = self._hash(leaf_data)
        for direction, sibling in proof:
            if direction == "right":
                current = self._hash(current + sibling)
            else:
                current = self._hash(sibling + current)
        return current == root

    def stats(self) -> Dict:
        return {"leaves": len(self.leaves), "root": self.root[:16], "layers": len(self.layers)}

def run():
    tree = MerkleTree()
    for i in range(8):
        tree.add_leaf(f"data_{i}")
    root = tree.build()
    print("Root:", root[:16])
    proof = tree.get_proof(3)
    print("Proof:", proof)
    print("Verify:", tree.verify("data_3", proof, root))
    print(tree.stats())

if __name__ == "__main__":
    run()
