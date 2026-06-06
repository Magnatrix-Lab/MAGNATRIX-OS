#!/usr/bin/env python3
"""
Caching Engine for MAGNATRIX-OS
LRU cache, TTL, memoization, distributed cache support.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import functools
import hashlib
import json
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

T = TypeVar('T')


class LRUCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300) -> None:
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[Any, float, Optional[float]]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            value, timestamp, ttl = self._cache[key]
            if ttl and time.time() - timestamp > ttl:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, time.time(), ttl or self._default_ttl)
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._cache.keys())

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {'size': len(self._cache), 'max_size': self._max_size}


class Memoizer:
    """Function memoization decorator."""

    def __init__(self, max_size: int = 1000, ttl: int = 300) -> None:
        self._cache = LRUCache(max_size, ttl)

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            key = self._make_key(args, kwargs)
            cached = self._cache.get(key)
            if cached is not None:
                return cached
            result = func(*args, **kwargs)
            self._cache.set(key, result)
            return result
        return wrapper

    def _make_key(self, args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> str:
        key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]


class CacheEngine:
    """Main cache orchestrator."""

    def __init__(self) -> None:
        self._caches: Dict[str, LRUCache] = {}

    def get_cache(self, name: str, max_size: int = 1000, ttl: int = 300) -> LRUCache:
        if name not in self._caches:
            self._caches[name] = LRUCache(max_size, ttl)
        return self._caches[name]

    def memoize(self, max_size: int = 1000, ttl: int = 300) -> Memoizer:
        return Memoizer(max_size, ttl)

    def clear_all(self) -> None:
        for cache in self._caches.values():
            cache.clear()


def _demo() -> None:
    print("=== Cache Engine Demo ===\n")
    cache = LRUCache(max_size=5, default_ttl=10)
    cache.set('key1', 'value1')
    cache.set('key2', 'value2')
    cache.set('key3', 'value3')
    print(f"Get key1: {cache.get('key1')}")
    cache.set('key4', 'value4')
    cache.set('key5', 'value5')
    cache.set('key6', 'value6')
    print(f"After eviction, key1: {cache.get('key1')}")
    print(f"Cache keys: {cache.keys()}")
    print("\n=== Cache Engine Demo Complete ===")


if __name__ == '__main__':
    _demo()
