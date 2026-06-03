"""
llm_inference_cache_native.py
MAGNATRIX-OS Inference Cache Engine
Native Python, stdlib only.
Provides prompt-based caching, semantic cache, TTL management, and cache hit analytics.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class CacheEntryStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    EVICTED = "evicted"


@dataclass
class CacheEntry:
    key: str
    prompt_hash: str
    response: str
    created_at: float
    ttl_seconds: float
    access_count: int = 0
    last_accessed: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: CacheEntryStatus = CacheEntryStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key, "created_at": self.created_at,
            "ttl": self.ttl_seconds, "access_count": self.access_count,
            "status": self.status.value,
        }

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl_seconds


class InferenceCacheEngine:
    """Prompt-based and semantic caching for LLM inference."""

    def __init__(self, max_size: int = 1000, default_ttl: float = 3600.0) -> None:
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def _hash_prompt(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def _semantic_key(self, prompt: str) -> str:
        # Simple semantic key: first 50 chars normalized
        normalized = prompt.lower().strip()[:50]
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def get(self, prompt: str, semantic: bool = False) -> Optional[CacheEntry]:
        key = self._semantic_key(prompt) if semantic else self._hash_prompt(prompt)
        entry = self._cache.get(key)
        if not entry:
            self._misses += 1
            return None
        if entry.is_expired:
            entry.status = CacheEntryStatus.EXPIRED
            self._misses += 1
            return None
        entry.access_count += 1
        entry.last_accessed = time.time()
        self._hits += 1
        return entry

    def set(self, prompt: str, response: str, ttl: Optional[float] = None,
            semantic: bool = False, metadata: Optional[Dict[str, Any]] = None) -> CacheEntry:
        key = self._semantic_key(prompt) if semantic else self._hash_prompt(prompt)
        ttl = ttl if ttl is not None else self.default_ttl
        entry = CacheEntry(
            key=key, prompt_hash=key, response=response,
            created_at=time.time(), ttl_seconds=ttl,
            metadata=metadata or {}
        )
        self._cache[key] = entry
        self._evict_if_needed()
        return entry

    def _evict_if_needed(self) -> None:
        if len(self._cache) > self.max_size:
            # Evict least accessed
            sorted_entries = sorted(self._cache.values(), key=lambda e: e.access_count)
            to_evict = sorted_entries[:len(sorted_entries) - self.max_size]
            for e in to_evict:
                e.status = CacheEntryStatus.EVICTED
                del self._cache[e.key]

    def invalidate(self, prompt: str, semantic: bool = False) -> bool:
        key = self._semantic_key(prompt) if semantic else self._hash_prompt(prompt)
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def invalidate_all(self) -> None:
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._cache), "max_size": self.max_size,
            "hits": self._hits, "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "expired": sum(1 for e in self._cache.values() if e.is_expired),
        }

    def get_entries(self) -> List[CacheEntry]:
        return list(self._cache.values())

    def preload(self, prompts_responses: Dict[str, str], ttl: Optional[float] = None) -> int:
        for prompt, response in prompts_responses.items():
            self.set(prompt, response, ttl)
        return len(prompts_responses)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Inference Cache Engine")
    print("=" * 60)

    engine = InferenceCacheEngine(max_size=100, default_ttl=60.0)

    print("\n--- Cache miss ---")
    entry = engine.get("What is the capital of France?")
    print(f"  Hit: {entry is not None}")

    print("\n--- Cache set ---")
    engine.set("What is the capital of France?", "Paris is the capital of France.")
    entry = engine.get("What is the capital of France?")
    print(f"  Hit: {entry is not None}")
    print(f"  Response: {entry.response if entry else 'N/A'}")

    print("\n--- Semantic cache ---")
    engine.set("Tell me the capital of France", "Paris is the capital of France.", semantic=True)
    entry = engine.get("What is the capital of France?", semantic=True)
    print(f"  Semantic hit: {entry is not None}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\n--- Preload ---")
    faqs = {
        "What is Python?": "Python is a programming language.",
        "What is AI?": "AI is artificial intelligence.",
    }
    engine.preload(faqs)
    print(f"  Preloaded: {len(faqs)}")
    print(engine.get_stats())

    print("\nInference Cache test complete.")


if __name__ == "__main__":
    run()
