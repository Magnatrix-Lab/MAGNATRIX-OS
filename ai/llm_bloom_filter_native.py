"""Bloom Filter - Probabilistic set membership for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import hashlib

@dataclass
class BloomFilter:
    size: int = 1024; hash_count: int = 3
    bit_array: List[int] = field(default_factory=list)

    def __post_init__(self):
        if not self.bit_array: self.bit_array = [0]*self.size

    def _hashes(self, item: str) -> List[int]:
        return [int(hashlib.md5(f"{item}{i}".encode()).hexdigest(), 16) % self.size for i in range(self.hash_count)]

    def add(self, item: str) -> None:
        for idx in self._hashes(item): self.bit_array[idx] = 1

    def contains(self, item: str) -> bool:
        return all(self.bit_array[idx] == 1 for idx in self._hashes(item))

    def stats(self) -> dict:
        ones = sum(self.bit_array)
        return {"size": self.size, "hash_count": self.hash_count, "fill_rate": round(ones/self.size, 4)}

def run():
    bf = BloomFilter(100, 3)
    for w in ["apple", "banana", "cherry"]: bf.add(w)
    print("Contains apple:", bf.contains("apple"))
    print("Contains grape:", bf.contains("grape"))
    print("Stats:", bf.stats())

if __name__ == "__main__": run()
