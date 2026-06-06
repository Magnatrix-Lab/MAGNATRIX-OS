#!/usr/bin/env python3
"""
Cache Manager for MAGNATRIX-OS
LRU in-memory cache + disk-backed cache with TTL invalidation,
key deduplication, and cache warming support.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")


class CacheEntry(Generic[T]):
    """A single cached item with metadata."""

    def __init__(self, key: str, value: T, ttl_seconds: Optional[float], tags: Optional[List[str]]) -> None:
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl_seconds
        self.expires_at = self.created_at + ttl_seconds if ttl_seconds else None
        self.access_count = 0
        self.last_accessed = self.created_at
        self.tags = tags or []
        self.size = self._estimate_size(value)

    @staticmethod
    def _estimate_size(value: Any) -> int:
        try:
            return len(json.dumps(value).encode("utf-8"))
        except Exception:
            return 1024

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class CacheManager(Generic[T]):
    """Multi-tier cache: in-memory LRU + disk persistence."""

    def __init__(self, max_memory_items: int = 1000, disk_dir: Optional[str] = None, max_disk_bytes: int = 50 * 1024 * 1024) -> None:
        self.max_memory = max_memory_items
        self.disk_dir = Path(disk_dir) if disk_dir else Path("/tmp/magnatrix_cache")
        self.disk_dir.mkdir(parents=True, exist_ok=True)
        self.max_disk = max_disk_bytes
        self._memory: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def _disk_path(self, key: str) -> Path:
        h = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.disk_dir / f"{h}.json"

    def _save_to_disk(self, entry: CacheEntry[T]) -> None:
        path = self._disk_path(entry.key)
        data = {
            "key": entry.key,
            "value": entry.value,
            "created_at": entry.created_at,
            "ttl": entry.ttl,
            "tags": entry.tags,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _load_from_disk(self, key: str) -> Optional[CacheEntry[T]]:
        path = self._disk_path(key)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            entry = CacheEntry(key, data["value"], data.get("ttl"), data.get("tags", []))
            entry.created_at = data["created_at"]
            entry.expires_at = entry.created_at + entry.ttl if entry.ttl else None
            return entry
        except Exception:
            return None

    def _prune_disk(self) -> None:
        files = sorted(self.disk_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        total = sum(f.stat().st_size for f in files)
        while total > self.max_disk and files:
            oldest = files.pop(0)
            total -= oldest.stat().st_size
            oldest.unlink()

    def get(self, key: str) -> Optional[T]:
        with self._lock:
            entry = self._memory.get(key)
            if entry:
                if entry.is_expired():
                    del self._memory[key]
                    self._misses += 1
                    return None
                entry.access_count += 1
                entry.last_accessed = time.time()
                self._memory.move_to_end(key)
                self._hits += 1
                return entry.value
            self._misses += 1
        # Try disk
        disk_entry = self._load_from_disk(key)
        if disk_entry and not disk_entry.is_expired():
            with self._lock:
                self._memory[key] = disk_entry
                self._memory.move_to_end(key)
                if len(self._memory) > self.max_memory:
                    self._evict_lru()
                self._hits += 1
            return disk_entry.value
        return None

    def set(self, key: str, value: T, ttl_seconds: Optional[float] = None, tags: Optional[List[str]] = None) -> None:
        entry = CacheEntry(key, value, ttl_seconds, tags)
        with self._lock:
            self._memory[key] = entry
            self._memory.move_to_end(key)
            if len(self._memory) > self.max_memory:
                self._evict_lru()
        self._save_to_disk(entry)
        self._prune_disk()

    def _evict_lru(self) -> None:
        while len(self._memory) > self.max_memory:
            oldest = next(iter(self._memory))
            del self._memory[oldest]
            self._evictions += 1

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._memory:
                del self._memory[key]
        path = self._disk_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def clear(self) -> None:
        with self._lock:
            self._memory.clear()
        for f in self.disk_dir.glob("*.json"):
            f.unlink()

    # ------------------------------------------------------------------
    # Deduplication & warming
    # ------------------------------------------------------------------

    def get_or_compute(self, key: str, compute: Callable[[], T], ttl_seconds: Optional[float] = None) -> T:
        value = self.get(key)
        if value is not None:
            return value
        value = compute()
        self.set(key, value, ttl_seconds)
        return value

    def warm(self, keys: List[str], compute: Callable[[str], T], ttl_seconds: Optional[float] = None) -> None:
        for key in keys:
            if key not in self._memory:
                try:
                    self.set(key, compute(key), ttl_seconds)
                except Exception:
                    pass

    def invalidate_by_tag(self, tag: str) -> int:
        with self._lock:
            to_remove = [k for k, e in self._memory.items() if tag in e.tags]
            for k in to_remove:
                del self._memory[k]
                path = self._disk_path(k)
                if path.exists():
                    path.unlink()
            return len(to_remove)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        total = len(self._memory)
        expired = sum(1 for e in self._memory.values() if e.is_expired())
        total_size = sum(e.size for e in self._memory.values())
        disk_files = list(self.disk_dir.glob("*.json"))
        disk_size = sum(f.stat().st_size for f in disk_files)
        return {
            "memory_items": total,
            "memory_size_bytes": total_size,
            "disk_items": len(disk_files),
            "disk_size_bytes": disk_size,
            "expired": expired,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(1, self._hits + self._misses),
            "evictions": self._evictions,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="magnatrix_cache_")
    cache = CacheManager(max_memory_items=5, disk_dir=tmp, max_disk_bytes=1024 * 1024)
    print("=== Cache Manager Demo ===\n")
    # Set items
    for i in range(10):
        cache.set(f"key_{i}", {"data": i * 10}, ttl_seconds=60, tags=["demo"])
    print(f"Set 10 items, memory max=5, so disk should hold some")
    # Get
    print(f"Get key_3: {cache.get('key_3')}")
    print(f"Get key_99 (missing): {cache.get('key_99')}")
    # Deduplication
    def compute():
        return {"expensive": "result", "ts": time.time()}
    result = cache.get_or_compute("expensive_key", compute, ttl_seconds=30)
    print(f"\nComputed & cached: {result}")
    result2 = cache.get_or_compute("expensive_key", compute, ttl_seconds=30)
    print(f"Cached hit (same ts): {result2}")
    # Stats
    print(f"\nStats: {cache.stats()}")
    # Cleanup
    import shutil
    shutil.rmtree(tmp)
    print("\nCleanup complete.")


if __name__ == "__main__":
    _demo()
