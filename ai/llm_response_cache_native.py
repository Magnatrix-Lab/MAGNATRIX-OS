"""LLM Response Cache — Native Python (stdlib only)."""
from __future__ import annotations
import time, hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class CacheEntry:
    key: str
    value: Any
    ttl: float
    created_at: float

class ResponseCache:
    def __init__(self, default_ttl: float = 300.0) -> None:
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}

    def _make_key(self, query: str) -> str:
        return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]

    def get(self, query: str) -> Optional[Any]:
        key = self._make_key(query)
        entry = self._cache.get(key)
        if not entry:
            return None
        if time.time() - entry.created_at > entry.ttl:
            del self._cache[key]
            return None
        return entry.value

    def set(self, query: str, value: Any, ttl: Optional[float] = None) -> None:
        key = self._make_key(query)
        self._cache[key] = CacheEntry(key, value, ttl or self.default_ttl, time.time())

    def clear(self) -> None:
        self._cache.clear()

    def prune(self) -> int:
        now = time.time()
        expired = [k for k, v in self._cache.items() if now - v.created_at > v.ttl]
        for k in expired:
            del self._cache[k]
        return len(expired)

    def get_stats(self) -> Dict[str, Any]:
        return {"entries": len(self._cache), "expired": sum(1 for v in self._cache.values() if time.time() - v.created_at > v.ttl)}

def run() -> None:
    print("Response Cache test")
    e = ResponseCache(default_ttl=60.0)
    e.set("hello", "Hello world!", ttl=10.0)
    e.set("weather", "Sunny and warm", ttl=300.0)
    print("  Get 'hello': " + str(e.get("hello")))
    print("  Stats before prune: " + str(e.get_stats()))
    e.prune()
    print("  Stats after prune: " + str(e.get_stats()))
    print("Response Cache test complete.")

if __name__ == "__main__":
    run()
