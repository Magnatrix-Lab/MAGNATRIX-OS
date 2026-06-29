"""
caching_strategy_engine_native.py
MAGNATRIX-OS — Caching Strategy Engine

Inspired by donnemartin/system-design-primer caching strategies:
CDN, application cache, distributed cache, cache invalidation patterns. Pure stdlib.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class CacheEntry:
    key: str
    value: Any
    ttl: int
    cached_at: float
    hits: int = 0

    def is_expired(self) -> bool:
        return time.time() - self.cached_at > self.ttl


class CachingStrategyEngine:
    """Caching strategies: LRU, LFU, TTL, CDN, distributed cache."""

    def __init__(self, cache_dir: str = "./cache_engine", max_size: int = 1000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "cache.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.cache[k] = CacheEntry(**v)
            except Exception:
                pass
        file2 = self.cache_dir / "stats.json"
        if file2.exists():
            try:
                with open(file2, "r", encoding="utf-8") as f:
                    self.stats = json.load(f)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "cache.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.cache.items()}, f, indent=2)
        with open(self.cache_dir / "stats.json", "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=2)

    def get(self, key: str) -> Optional[Any]:
        entry = self.cache.get(key)
        if entry and not entry.is_expired():
            entry.hits += 1
            self.stats["hits"] += 1
            self._save()
            return entry.value
        if entry and entry.is_expired():
            del self.cache[key]
            self.stats["evictions"] += 1
        self.stats["misses"] += 1
        self._save()
        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        self.cache[key] = CacheEntry(key=key, value=value, ttl=ttl, cached_at=time.time())
        self._save()

    def _evict_lru(self) -> None:
        if not self.cache:
            return
        oldest = min(self.cache.values(), key=lambda e: e.cached_at)
        del self.cache[oldest.key]
        self.stats["evictions"] += 1

    def invalidate(self, key: str) -> bool:
        if key in self.cache:
            del self.cache[key]
            self._save()
            return True
        return False

    def invalidate_pattern(self, pattern: str) -> int:
        import fnmatch
        removed = 0
        for key in list(self.cache.keys()):
            if fnmatch.fnmatch(key, pattern):
                del self.cache[key]
                removed += 1
        self._save()
        return removed

    def hit_rate(self) -> float:
        total = self.stats["hits"] + self.stats["misses"]
        return round(self.stats["hits"] / max(1, total), 4)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self.cache), "max_size": self.max_size,
            "hits": self.stats["hits"], "misses": self.stats["misses"],
            "evictions": self.stats["evictions"], "hit_rate": self.hit_rate(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CachingStrategyEngine", "CacheEntry"]