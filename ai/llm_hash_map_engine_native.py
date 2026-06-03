"""Hash Map Engine - Custom hash map for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class HashMapEngine:
    capacity: int = 16
    buckets: List[List[Tuple[str, str]]] = field(default_factory=list)
    size: int = 0

    def __post_init__(self):
        if not self.buckets: self.buckets = [[] for _ in range(self.capacity)]

    def _hash(self, key: str) -> int:
        return sum(ord(c) for c in key) % self.capacity

    def put(self, key: str, value: str) -> None:
        idx = self._hash(key)
        for i, (k, v) in enumerate(self.buckets[idx]):
            if k == key: self.buckets[idx][i] = (key, value); return
        self.buckets[idx].append((key, value))
        self.size += 1
        if self.size / self.capacity > 0.75: self._resize()

    def get(self, key: str) -> Optional[str]:
        idx = self._hash(key)
        for k, v in self.buckets[idx]:
            if k == key: return v
        return None

    def _resize(self) -> None:
        old = self.buckets; self.capacity *= 2; self.buckets = [[] for _ in range(self.capacity)]; self.size = 0
        for bucket in old:
            for k, v in bucket: self.put(k, v)

    def stats(self) -> dict:
        return {"capacity": self.capacity, "size": self.size, "load": round(self.size/self.capacity, 4)}

def run():
    hm = HashMapEngine()
    hm.put("a", "1"); hm.put("b", "2"); hm.put("c", "3")
    print("Get a:", hm.get("a"))
    print("Stats:", hm.stats())

if __name__ == "__main__": run()
