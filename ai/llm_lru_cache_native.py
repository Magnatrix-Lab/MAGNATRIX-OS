"""LRU Cache - Least recently used cache for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import OrderedDict

@dataclass
class LRUCache:
    capacity: int = 10
    cache: OrderedDict = field(default_factory=OrderedDict)

    def get(self, key: str) -> Optional[str]:
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key: str, value: str) -> None:
        if key in self.cache: self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity: self.cache.popitem(last=False)

    def stats(self) -> dict:
        return {"capacity": self.capacity, "size": len(self.cache), "keys": list(self.cache.keys())}

def run():
    cache = LRUCache(3)
    cache.put("a", "1"); cache.put("b", "2"); cache.put("c", "3")
    cache.get("a"); cache.put("d", "4")
    print("Keys:", list(cache.cache.keys()))
    print("Stats:", cache.stats())

if __name__ == "__main__": run()
