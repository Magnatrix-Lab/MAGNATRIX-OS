"""KV Cache Manager — Key-value cache for efficient LLM inference.

Modul ini menyediakan:
- KVCacheEntry untuk individual KV cache entries
- KVCache untuk cache management dengan eviction policies
- CacheEvictionPolicy untuk LRU, LFU, FIFO eviction
- CacheCompressor untuk compress cache entries
- KVCacheManager untuk end-to-end KV cache management
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class EvictionPolicy(Enum):
    LRU = auto()
    LFU = auto()
    FIFO = auto()
    TTL = auto()


@dataclass
class KVCacheEntry:
    """Single KV cache entry."""
    entry_id: str
    key: str
    value: Any
    token_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl


class KVCache:
    """Cache with configurable eviction policy."""

    def __init__(self, max_size: int = 1000, policy: EvictionPolicy = EvictionPolicy.LRU):
        self.max_size = max_size
        self.policy = policy
        self._entries: Dict[str, KVCacheEntry] = {}
        self._order: List[str] = []  # For FIFO/LRU ordering
        self._total_tokens: int = 0

    def get(self, key: str) -> Optional[Any]:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            self._remove(key)
            return None
        entry.last_accessed = time.time()
        entry.access_count += 1
        if self.policy == EvictionPolicy.LRU:
            self._order.remove(key)
            self._order.append(key)
        return entry.value

    def put(self, key: str, value: Any, token_count: int = 0, ttl: Optional[float] = None) -> None:
        if key in self._entries:
            self._remove(key)
        entry = KVCacheEntry(
            entry_id=str(uuid.uuid4())[:12],
            key=key,
            value=value,
            token_count=token_count,
            ttl=ttl,
        )
        self._entries[key] = entry
        self._order.append(key)
        self._total_tokens += token_count
        self._evict_if_needed()

    def _remove(self, key: str) -> None:
        entry = self._entries.pop(key, None)
        if entry:
            self._order.remove(key)
            self._total_tokens -= entry.token_count

    def _evict_if_needed(self) -> None:
        while len(self._entries) > self.max_size:
            if self.policy == EvictionPolicy.FIFO:
                key = self._order[0]
            elif self.policy == EvictionPolicy.LRU:
                key = self._order[0]
            elif self.policy == EvictionPolicy.LFU:
                key = min(self._entries, lambda k: (self._entries[k].access_count, self._entries[k].last_accessed))
            elif self.policy == EvictionPolicy.TTL:
                expired = [k for k, e in self._entries.items() if e.is_expired()]
                if expired:
                    key = expired[0]
                else:
                    key = self._order[0]
            else:
                key = self._order[0]
            self._remove(key)

    def clear(self) -> None:
        self._entries.clear()
        self._order.clear()
        self._total_tokens = 0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self._entries),
            "max_size": self.max_size,
            "total_tokens": self._total_tokens,
            "policy": self.policy.name,
            "hit_rate": self._calculate_hit_rate(),
        }

    def _calculate_hit_rate(self) -> float:
        if not self._entries:
            return 0.0
        total_access = sum(e.access_count for e in self._entries.values())
        return total_access / max(len(self._entries), 1)

    def get_all_keys(self) -> List[str]:
        return list(self._entries.keys())


class CacheCompressor:
    """Compress cache entries to save memory."""

    def __init__(self, compression_ratio: float = 0.5):
        self.ratio = compression_ratio

    def compress(self, entry: KVCacheEntry) -> KVCacheEntry:
        # Simulated compression: truncate value representation
        if isinstance(entry.value, list) and len(entry.value) > 10:
            new_value = entry.value[:int(len(entry.value) * self.ratio)]
            return KVCacheEntry(
                entry_id=entry.entry_id,
                key=entry.key,
                value=new_value,
                token_count=int(entry.token_count * self.ratio),
                created_at=entry.created_at,
                last_accessed=entry.last_accessed,
                access_count=entry.access_count,
                ttl=entry.ttl,
            )
        return entry

    def compress_all(self, cache: KVCache) -> int:
        compressed = 0
        for key in list(cache._entries.keys()):
            entry = cache._entries[key]
            new_entry = self.compress(entry)
            if new_entry.token_count < entry.token_count:
                cache._entries[key] = new_entry
                cache._total_tokens -= (entry.token_count - new_entry.token_count)
                compressed += 1
        return compressed


class KVCacheManager:
    """End-to-end KV cache management."""

    def __init__(self, max_size: int = 1000, policy: EvictionPolicy = EvictionPolicy.LRU):
        self.cache = KVCache(max_size, policy)
        self.compressor = CacheCompressor()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        result = self.cache.get(key)
        if result is not None:
            self._hits += 1
        else:
            self._misses += 1
        return result

    def put(self, key: str, value: Any, token_count: int = 0, ttl: Optional[float] = None) -> None:
        self.cache.put(key, value, token_count, ttl)

    def compute(self, key: str, compute_fn: Callable[[], Any], token_count: int = 0) -> Any:
        result = self.get(key)
        if result is not None:
            return result
        result = compute_fn()
        self.put(key, result, token_count)
        return result

    def compress(self) -> int:
        return self.compressor.compress_all(self.cache)

    def get_stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            **self.cache.get_stats(),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(total, 1),
            "miss_rate": self._misses / max(total, 1),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.get_stats(),
                "keys": self.cache.get_all_keys()[:20],
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("KV CACHE MANAGER DEMO")
    print("=" * 70)

    # 1. Basic cache
    print("\n[1] Basic Cache (LRU)")
    cache = KVCacheManager(max_size=5, policy=EvictionPolicy.LRU)
    for i in range(7):
        cache.put(f"key-{i}", f"value-{i}", token_count=10)
    print(f"  Keys after 7 puts: {cache.cache.get_all_keys()}")
    print(f"  Stats: {cache.get_stats()}")

    # 2. Get and hit tracking
    print("\n[2] Hit Tracking")
    for i in range(5):
        result = cache.get(f"key-{i}")
        print(f"  get(key-{i}): {'HIT' if result else 'MISS'}")
    print(f"  Stats: {cache.get_stats()}")

    # 3. Compute pattern
    print("\n[3] Compute Pattern")
    def expensive_compute():
        return "Expensive result"
    r1 = cache.compute("expensive", expensive_compute, token_count=20)
    r2 = cache.compute("expensive", expensive_compute, token_count=20)
    print(f"  First compute: {r1}")
    print(f"  Second compute (cached): {r2}")
    print(f"  Stats: {cache.get_stats()}")

    # 4. TTL
    print("\n[4] TTL Eviction")
    cache_ttl = KVCacheManager(max_size=100, policy=EvictionPolicy.TTL)
    cache_ttl.put("short", "value1", ttl=0.01)
    time.sleep(0.02)
    result = cache_ttl.get("short")
    print(f"  After TTL expiry: {'HIT' if result else 'MISS'}")

    # 5. FIFO policy
    print("\n[5] FIFO Policy")
    cache_fifo = KVCacheManager(max_size=3, policy=EvictionPolicy.FIFO)
    for i in range(5):
        cache_fifo.put(f"fifo-{i}", f"val-{i}")
    print(f"  Keys: {cache_fifo.cache.get_all_keys()}")

    # 6. Compression
    print("\n[6] Compression")
    cache_big = KVCacheManager(max_size=100)
    cache_big.put("big", list(range(100)), token_count=100)
    print(f"  Before compress: {cache_big.get_stats()}")
    cache_big.compress()
    print(f"  After compress: {cache_big.get_stats()}")

    # 7. Export
    print("\n[7] Export")
    cache.export("/tmp/kv_cache.json")
    print("  Exported to /tmp/kv_cache.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
