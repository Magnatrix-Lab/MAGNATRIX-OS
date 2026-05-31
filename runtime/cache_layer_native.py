
"""
runtime/cache_layer_native.py — MAGNATRIX-OS Cache Layer

Redis-like in-memory cache with TTL, eviction, and persistence.
Pure Python, stdlib only. Zero dependencies.

Components:
    • CacheLayer — main cache orchestrator
    • MemoryCache — in-memory LRU cache with TTL
    • TieredCache — L1 (memory) + L2 (disk) two-tier cache
    • CachePolicy — eviction policy (LRU, LFU, FIFO, TTL)
    • CacheEntry — cache entry with metadata
    • CacheStats — hit rate, miss rate, eviction rate
    • DiskCache — persistent disk-based cache
"""
from __future__ import annotations

import gzip
import json
import os
import pickle
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ════════════════════════════════════════════════════════════════════════════
# CacheEntry
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    hits: int = 0
    size: int = 0
    tags: Set[str] = field(default_factory=set)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def ttl(self) -> Optional[float]:
        if self.expires_at is None:
            return None
        remaining = self.expires_at - time.time()
        return max(0.0, remaining)

    def touch(self) -> None:
        self.hits += 1


# ════════════════════════════════════════════════════════════════════════════
# CachePolicy
# ════════════════════════════════════════════════════════════════════════════

class EvictionPolicy(Enum):
    LRU = "lru"      # Least Recently Used
    LFU = "lfu"      # Least Frequently Used
    FIFO = "fifo"    # First In First Out
    TTL = "ttl"      # Time To Live (expire only, no eviction on size)


@dataclass
class CachePolicy:
    max_size: int = 1000              # max number of entries
    max_memory: int = 50 * 1024 * 1024  # 50MB
    eviction: EvictionPolicy = EvictionPolicy.LRU
    default_ttl: Optional[float] = None
    compress_threshold: int = 1024     # compress values > 1KB
    persist_interval: Optional[float] = 60.0  # auto-save every 60s


# ════════════════════════════════════════════════════════════════════════════
# CacheStats
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    writes: int = 0
    deletes: int = 0

    @property
    def total_requests(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        total = self.total_requests
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        total = self.total_requests
        return self.misses / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "writes": self.writes,
            "deletes": self.deletes,
            "hit_rate": round(self.hit_rate, 4),
            "miss_rate": round(self.miss_rate, 4),
        }


# ════════════════════════════════════════════════════════════════════════════
# MemoryCache
# ════════════════════════════════════════════════════════════════════════════

class MemoryCache:
    """In-memory LRU cache with TTL support."""

    def __init__(self, policy: Optional[CachePolicy] = None, namespace: str = "default"):
        self.policy = policy or CachePolicy()
        self.namespace = namespace
        self._data: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats()
        self._lock = threading.RLock()
        self._current_memory = 0
        self._cleanup_interval = 30.0
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = True
        self._start_cleanup()

    def _start_cleanup(self) -> None:
        def cleanup_loop():
            while self._running:
                time.sleep(self._cleanup_interval)
                if self._running:
                    self._cleanup_expired()
        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_expired(self) -> int:
        """Remove expired entries. Returns count removed."""
        with self._lock:
            expired = [k for k, e in self._data.items() if e.is_expired()]
            for k in expired:
                entry = self._data.pop(k)
                self._current_memory -= entry.size
                self._stats.expirations += 1
            return len(expired)

    def _evict_if_needed(self, new_size: int) -> None:
        """Evict entries if cache is over capacity."""
        with self._lock:
            while (len(self._data) >= self.policy.max_size or
                   self._current_memory + new_size > self.policy.max_memory):
                if not self._data:
                    break

                if self.policy.eviction == EvictionPolicy.LRU:
                    key, entry = self._data.popitem(last=False)
                elif self.policy.eviction == EvictionPolicy.LFU:
                    key = min(self._data, key=lambda k: self._data[k].hits)
                    entry = self._data.pop(key)
                elif self.policy.eviction == EvictionPolicy.FIFO:
                    key, entry = self._data.popitem(last=False)
                else:  # TTL — just remove expired
                    break

                self._current_memory -= entry.size
                self._stats.evictions += 1

    def _serialize_value(self, value: Any) -> Tuple[bytes, int]:
        """Serialize and optionally compress value. Returns (data, size)."""
        data = pickle.dumps(value)
        size = len(data)
        if size > self.policy.compress_threshold:
            data = gzip.compress(data)
        return data, size

    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value, handling compression."""
        try:
            return pickle.loads(data)
        except Exception:
            # Try decompressing
            try:
                return pickle.loads(gzip.decompress(data))
            except Exception:
                return data

    def set(
        self, key: str, value: Any,
        ttl: Optional[float] = None,
        tags: Optional[Set[str]] = None,
    ) -> bool:
        """Set a cache entry."""
        data, size = self._serialize_value(value)

        expires = None
        if ttl is not None:
            expires = time.time() + ttl
        elif self.policy.default_ttl is not None:
            expires = time.time() + self.policy.default_ttl

        entry = CacheEntry(
            key=key, value=data, created_at=time.time(),
            expires_at=expires, size=size, tags=tags or set(),
        )

        with self._lock:
            self._evict_if_needed(size)
            if key in self._data:
                self._current_memory -= self._data[key].size
            self._data[key] = entry
            self._current_memory += size
            self._stats.writes += 1

        return True

    def get(self, key: str, default: Any = None) -> Any:
        """Get a cache entry."""
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self._stats.misses += 1
                return default

            if entry.is_expired():
                self._current_memory -= entry.size
                del self._data[key]
                self._stats.expirations += 1
                self._stats.misses += 1
                return default

            entry.touch()
            if self.policy.eviction == EvictionPolicy.LRU:
                self._data.move_to_end(key)

            self._stats.hits += 1
            return self._deserialize_value(entry.value)

    def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        with self._lock:
            if key in self._data:
                entry = self._data.pop(key)
                self._current_memory -= entry.size
                self._stats.deletes += 1
                return True
            return False

    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all entries with a given tag."""
        with self._lock:
            to_remove = [k for k, e in self._data.items() if tag in e.tags]
            for k in to_remove:
                entry = self._data.pop(k)
                self._current_memory -= entry.size
            return len(to_remove)

    def exists(self, key: str) -> bool:
        with self._lock:
            entry = self._data.get(key)
            return entry is not None and not entry.is_expired()

    def ttl(self, key: str) -> Optional[float]:
        with self._lock:
            entry = self._data.get(key)
            if entry is None or entry.is_expired():
                return None
            return entry.ttl()

    def keys(self) -> List[str]:
        with self._lock:
            return [k for k, e in self._data.items() if not e.is_expired()]

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._current_memory = 0

    def stats(self) -> Dict[str, Any]:
        return self._stats.to_dict()

    def info(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "namespace": self.namespace,
                "entries": len(self._data),
                "memory_used": self._current_memory,
                "memory_limit": self.policy.max_memory,
                "size_limit": self.policy.max_size,
                "eviction_policy": self.policy.eviction.value,
                **self.stats(),
            }

    def close(self) -> None:
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=1.0)


# ════════════════════════════════════════════════════════════════════════════
# DiskCache
# ════════════════════════════════════════════════════════════════════════════

class DiskCache:
    """Persistent disk-based cache with TTL."""

    def __init__(self, cache_dir: str = ".cache/magnatrix", max_size: int = 100 * 1024 * 1024):
        self.cache_dir = cache_dir
        self.max_size = max_size
        self._current_size = 0
        self._lock = threading.RLock()
        os.makedirs(cache_dir, exist_ok=True)
        self._load_index()

    def _key_to_path(self, key: str) -> str:
        """Convert key to file path."""
        import hashlib
        h = hashlib.sha256(key.encode()).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"{h}.cache")

    def _load_index(self) -> None:
        """Load existing cache files."""
        self._current_size = 0
        for f in os.listdir(self.cache_dir):
            if f.endswith(".cache"):
                path = os.path.join(self.cache_dir, f)
                self._current_size += os.path.getsize(path)

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        path = self._key_to_path(key)
        data = {
            "value": value,
            "created": time.time(),
            "ttl": ttl,
        }
        raw = pickle.dumps(data)
        compressed = gzip.compress(raw) if len(raw) > 1024 else raw

        with self._lock:
            self._current_size += len(compressed)
            self._cleanup_if_needed()
            with open(path, "wb") as f:
                f.write(compressed)
        return True

    def get(self, key: str, default: Any = None) -> Any:
        path = self._key_to_path(key)
        if not os.path.exists(path):
            return default

        try:
            with open(path, "rb") as f:
                data = f.read()
            try:
                raw = gzip.decompress(data)
            except Exception:
                raw = data
            entry = pickle.loads(raw)

            if entry.get("ttl") is not None:
                if time.time() > entry["created"] + entry["ttl"]:
                    os.remove(path)
                    return default

            return entry["value"]
        except Exception:
            return default

    def delete(self, key: str) -> bool:
        path = self._key_to_path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def _cleanup_if_needed(self) -> None:
        """Remove oldest files if over size limit."""
        if self._current_size <= self.max_size:
            return

        files = []
        for f in os.listdir(self.cache_dir):
            path = os.path.join(self.cache_dir, f)
            if f.endswith(".cache"):
                files.append((path, os.path.getmtime(path)))

        files.sort(key=lambda x: x[1])

        for path, _ in files:
            if self._current_size <= self.max_size * 0.8:
                break
            size = os.path.getsize(path)
            os.remove(path)
            self._current_size -= size

    def clear(self) -> None:
        for f in os.listdir(self.cache_dir):
            if f.endswith(".cache"):
                os.remove(os.path.join(self.cache_dir, f))
        self._current_size = 0


# ════════════════════════════════════════════════════════════════════════════
# TieredCache — L1 (memory) + L2 (disk)
# ════════════════════════════════════════════════════════════════════════════

class TieredCache:
    """Two-tier cache: L1 in-memory, L2 on disk."""

    def __init__(
        self,
        memory_policy: Optional[CachePolicy] = None,
        disk_dir: str = ".cache/magnatrix",
    ):
        self.l1 = MemoryCache(policy=memory_policy, namespace="l1")
        self.l2 = DiskCache(cache_dir=disk_dir)

    def get(self, key: str, default: Any = None) -> Any:
        # Try L1 first
        value = self.l1.get(key)
        if value is not None:
            return value

        # Try L2
        value = self.l2.get(key)
        if value is not None:
            # Promote to L1
            self.l1.set(key, value)
            return value

        return default

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        self.l1.set(key, value, ttl=ttl)
        self.l2.set(key, value, ttl=ttl)
        return True

    def delete(self, key: str) -> bool:
        self.l1.delete(key)
        self.l2.delete(key)
        return True

    def clear(self) -> None:
        self.l1.clear()
        self.l2.clear()

    def stats(self) -> Dict[str, Any]:
        return {
            "l1": self.l1.stats(),
            "l2": {"current_size": self.l2._current_size},
        }


# ════════════════════════════════════════════════════════════════════════════
# CacheLayer — main orchestrator
# ════════════════════════════════════════════════════════════════════════════

class CacheLayer:
    """Main cache orchestrator with multiple backends."""

    def __init__(self):
        self._caches: Dict[str, Union[MemoryCache, DiskCache, TieredCache]] = {}
        self._lock = threading.Lock()

    def create_memory(self, name: str, policy: Optional[CachePolicy] = None) -> MemoryCache:
        with self._lock:
            cache = MemoryCache(policy=policy, namespace=name)
            self._caches[name] = cache
            return cache

    def create_disk(self, name: str, cache_dir: str) -> DiskCache:
        with self._lock:
            cache = DiskCache(cache_dir=cache_dir)
            self._caches[name] = cache
            return cache

    def create_tiered(self, name: str, memory_policy: Optional[CachePolicy] = None, disk_dir: str = ".cache/magnatrix") -> TieredCache:
        with self._lock:
            cache = TieredCache(memory_policy=memory_policy, disk_dir=disk_dir)
            self._caches[name] = cache
            return cache

    def get(self, name: str) -> Optional[Union[MemoryCache, DiskCache, TieredCache]]:
        with self._lock:
            return self._caches.get(name)

    def remove(self, name: str) -> bool:
        with self._lock:
            if name in self._caches:
                cache = self._caches.pop(name)
                if hasattr(cache, 'close'):
                    cache.close()
                return True
            return False

    def stats(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {name: cache.stats() for name, cache in self._caches.items()}


# ════════════════════════════════════════════════════════════════════════════
# DEMO / SELF-TEST
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Cache Layer — Self-Test")
    print("=" * 60)

    # Test 1: MemoryCache basic operations
    print("\n[1] MemoryCache basic operations")
    cache = MemoryCache(
        policy=CachePolicy(max_size=100, max_memory=10*1024*1024, eviction=EvictionPolicy.LRU),
        namespace="test"
    )

    cache.set("key1", "value1", ttl=60.0)
    cache.set("key2", {"nested": "data"}, ttl=60.0)
    cache.set("key3", [1, 2, 3])

    assert cache.get("key1") == "value1"
    assert cache.get("key2") == {"nested": "data"}
    assert cache.get("key3") == [1, 2, 3]
    assert cache.get("missing") is None
    print("  ✓ Basic set/get works")

    # Test 2: TTL expiration
    print("\n[2] TTL expiration")
    cache.set("temp", "data", ttl=0.1)
    assert cache.get("temp") == "data"
    time.sleep(0.15)
    assert cache.get("temp") is None
    print("  ✓ TTL expiration works")

    # Test 3: LRU eviction
    print("\n[3] LRU eviction")
    small_cache = MemoryCache(
        policy=CachePolicy(max_size=3, eviction=EvictionPolicy.LRU),
        namespace="lru_test"
    )
    small_cache.set("a", 1)
    small_cache.set("b", 2)
    small_cache.set("c", 3)
    small_cache.get("a")  # Touch a
    small_cache.set("d", 4)  # Should evict b (least recently used)

    assert small_cache.get("a") == 1
    assert small_cache.get("b") is None
    assert small_cache.get("c") == 3
    assert small_cache.get("d") == 4
    print("  ✓ LRU eviction works")

    # Test 4: Tag invalidation
    print("\n[4] Tag invalidation")
    cache.set("user:1", {"name": "Alice"}, tags={"users"})
    cache.set("user:2", {"name": "Bob"}, tags={"users"})
    cache.set("config:1", {"theme": "dark"}, tags={"config"})

    removed = cache.invalidate_by_tag("users")
    assert removed == 2
    assert cache.get("user:1") is None
    assert cache.get("config:1") is not None
    print("  ✓ Tag invalidation works")

    # Test 5: DiskCache
    print("\n[5] DiskCache")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        disk = DiskCache(cache_dir=tmpdir, max_size=10*1024*1024)
        disk.set("disk_key", "disk_value", ttl=3600)
        assert disk.get("disk_key") == "disk_value"
        disk.delete("disk_key")
        assert disk.get("disk_key") is None
        print("  ✓ DiskCache works")

    # Test 6: TieredCache
    print("\n[6] TieredCache")
    tiered = TieredCache(
        memory_policy=CachePolicy(max_size=10, eviction=EvictionPolicy.LRU),
        disk_dir=".cache/test_tiered"
    )
    tiered.set("tiered_key", "tiered_value", ttl=3600)
    assert tiered.get("tiered_key") == "tiered_value"
    print("  ✓ TieredCache works")

    # Test 7: Stats
    print("\n[7] Cache stats")
    stats = cache.stats()
    assert "hit_rate" in stats
    assert "miss_rate" in stats
    print(f"  ✓ Stats: {stats}")

    # Test 8: CacheLayer orchestrator
    print("\n[8] CacheLayer orchestrator")
    layer = CacheLayer()
    mem = layer.create_memory("session_cache", CachePolicy(max_size=1000))
    mem.set("session:123", {"user": "test"})
    assert layer.get("session_cache").get("session:123") == {"user": "test"}
    print("  ✓ CacheLayer works")

    # Test 9: Compression
    print("\n[9] Compression")
    big_data = "x" * 10000
    cache.set("big", big_data)
    assert cache.get("big") == big_data
    print("  ✓ Large value compression works")

    # Test 10: Info
    print("\n[10] Cache info")
    info = cache.info()
    assert "entries" in info
    assert "memory_used" in info
    print(f"  ✓ Info: {info}")

    cache.close()
    print("\n" + "=" * 60)
    print("All self-tests passed ✓")
    print("=" * 60)
