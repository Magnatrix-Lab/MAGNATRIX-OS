"""DHT Engine - Distributed hash table for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import hashlib

@dataclass
class DHTEngine:
    nodes: List[str] = field(default_factory=list)
    data: Dict[str, str] = field(default_factory=dict)

    def hash_key(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def get_node(self, key: str) -> str:
        if not self.nodes: return ""
        h = self.hash_key(key) % len(self.nodes)
        return self.nodes[h]

    def put(self, key: str, value: str) -> None:
        self.data[key] = value

    def get(self, key: str) -> Optional[str]:
        return self.data.get(key)

    def stats(self) -> dict:
        return {"nodes": len(self.nodes), "entries": len(self.data)}

def run():
    dht = DHTEngine()
    dht.nodes = ["node1", "node2", "node3"]
    dht.put("key1", "value1")
    print("Node for key1:", dht.get_node("key1"))
    print("Value:", dht.get("key1"))
    print("Stats:", dht.stats())

if __name__ == "__main__": run()
