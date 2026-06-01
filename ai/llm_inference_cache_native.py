"""Inference Cache — Semantic response caching with similarity-based retrieval.

Modul ini menyediakan:
- SemanticCache untuk menyimpan response berdasarkan query embedding
- LRU eviction dengan TTL support
- Similarity threshold untuk cache hit/miss
- Cache analytics (hit rate, savings, eviction stats)
- Multi-tier cache (memory + disk) dengan serialization
"""

from __future__ import annotations

import json
import time
import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class CacheTier(Enum):
    MEMORY = auto()
    DISK = auto()


@dataclass
class CacheEntry:
    """Single cached response entry."""
    key: str
    query_hash: str
    query_text: str
    response: str
    embedding: Optional[List[float]] = None
    timestamp: float = field(default_factory=time.time)
    ttl: float = 3600.0  # seconds
    hit_count: int = 0
    model_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl

    def touch(self) -> None:
        self.hit_count += 1


class EmbeddingCache:
    """Simulated embedding storage for semantic similarity."""

    def __init__(self, dim: int = 128):
        self.dim = dim
        self._embeddings: Dict[str, List[float]] = {}

    def embed(self, text: str) -> List[float]:
        # Simulated embedding: hash-based deterministic vector
        if text in self._embeddings:
            return self._embeddings[text]
        h = hashlib.sha256(text.encode()).hexdigest()
        vec = [((int(h[i:i+4], 16) % 1000) / 1000.0 - 0.5) * 2 for i in range(0, 64, 4)]
        # Pad or truncate to dim
        vec = (vec * ((self.dim // len(vec)) + 1))[:self.dim]
        self._embeddings[text] = vec
        return vec

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class SemanticCache:
    """Semantic cache with similarity-based retrieval."""

    def __init__(self, max_size: int = 1000, similarity_threshold: float = 0.92,
                 default_ttl: float = 3600.0, embedding_dim: int = 128):
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.default_ttl = default_ttl
        self.embedding = EmbeddingCache(embedding_dim)
        self._entries: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # LRU order
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._savings = 0.0  # estimated cost savings

    def _make_key(self, query: str, model_id: str) -> str:
        return hashlib.sha256(f"{model_id}:{query}".encode()).hexdigest()[:16]

    def get(self, query: str, model_id: str = "") -> Optional[str]:
        # First try exact match
        key = self._make_key(query, model_id)
        if key in self._entries:
            entry = self._entries[key]
            if not entry.is_expired():
                entry.touch()
                self._hits += 1
                self._update_lru(key)
                self._savings += self._estimate_cost(query)
                return entry.response
            else:
                del self._entries[key]
                self._access_order.remove(key)

        # Try semantic similarity
        query_emb = self.embedding.embed(query)
        best_match: Optional[CacheEntry] = None
        best_score = 0.0

        for entry in self._entries.values():
            if entry.is_expired():
                continue
            if entry.model_id and entry.model_id != model_id:
                continue
            if entry.embedding is None:
                entry.embedding = self.embedding.embed(entry.query_text)
            score = self.embedding.cosine_similarity(query_emb, entry.embedding)
            if score > best_score and score >= self.similarity_threshold:
                best_score = score
                best_match = entry

        if best_match:
            best_match.touch()
            self._hits += 1
            self._update_lru(best_match.key)
            self._savings += self._estimate_cost(query)
            return best_match.response

        self._misses += 1
        return None

    def set(self, query: str, response: str, model_id: str = "", ttl: Optional[float] = None,
            metadata: Optional[Dict[str, Any]] = None) -> CacheEntry:
        key = self._make_key(query, model_id)
        ttl = ttl or self.default_ttl

        # Evict if at capacity
        if len(self._entries) >= self.max_size and key not in self._entries:
            self._evict_lru()

        entry = CacheEntry(
            key=key,
            query_hash=hashlib.sha256(query.encode()).hexdigest()[:12],
            query_text=query,
            response=response,
            embedding=self.embedding.embed(query),
            ttl=ttl,
            model_id=model_id,
            metadata=metadata or {}
        )
        self._entries[key] = entry
        if key not in self._access_order:
            self._access_order.append(key)
        return entry

    def invalidate(self, pattern: Optional[str] = None) -> int:
        if pattern is None:
            count = len(self._entries)
            self._entries.clear()
            self._access_order.clear()
            return count
        to_remove = [k for k, e in self._entries.items() if pattern in e.query_text]
        for k in to_remove:
            del self._entries[k]
            self._access_order.remove(k)
        return len(to_remove)

    def _evict_lru(self) -> None:
        if self._access_order:
            oldest = self._access_order.pop(0)
            if oldest in self._entries:
                del self._entries[oldest]
                self._evictions += 1

    def _update_lru(self, key: str) -> None:
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def _estimate_cost(self, query: str) -> float:
        # Rough estimate: $0.01 per query
        return 0.01

    def get_stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._entries),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(total, 1), 4),
            "evictions": self._evictions,
            "estimated_savings": round(self._savings, 4),
            "expired": sum(1 for e in self._entries.values() if e.is_expired()),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.get_stats(),
                "entries": [{
                    "key": e.key,
                    "query": e.query_text[:100],
                    "response": e.response[:100],
                    "hits": e.hit_count,
                    "model": e.model_id,
                    "timestamp": e.timestamp,
                } for e in self._entries.values()]
            }, f, indent=2)


class MultiTierCache:
    """Multi-tier cache: L1 (fast memory) + L2 (disk)."""

    def __init__(self, l1_size: int = 500, l2_size: int = 5000,
                 similarity_threshold: float = 0.92):
        self.l1 = SemanticCache(max_size=l1_size, similarity_threshold=similarity_threshold)
        self.l2 = SemanticCache(max_size=l2_size, similarity_threshold=similarity_threshold)
        self._l1_hits = 0
        self._l2_hits = 0
        self._misses = 0

    def get(self, query: str, model_id: str = "") -> Optional[str]:
        # Try L1 first
        result = self.l1.get(query, model_id)
        if result:
            self._l1_hits += 1
            return result
        # Try L2
        result = self.l2.get(query, model_id)
        if result:
            self._l2_hits += 1
            # Promote to L1
            self.l1.set(query, result, model_id)
            return result
        self._misses += 1
        return None

    def set(self, query: str, response: str, model_id: str = "",
            tier: CacheTier = CacheTier.MEMORY) -> CacheEntry:
        if tier == CacheTier.MEMORY:
            return self.l1.set(query, response, model_id)
        else:
            return self.l2.set(query, response, model_id)

    def get_stats(self) -> Dict[str, Any]:
        total = self._l1_hits + self._l2_hits + self._misses
        return {
            "l1": self.l1.get_stats(),
            "l2": self.l2.get_stats(),
            "l1_hits": self._l1_hits,
            "l2_hits": self._l2_hits,
            "misses": self._misses,
            "overall_hit_rate": round((self._l1_hits + self._l2_hits) / max(total, 1), 4),
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("INFERENCE CACHE DEMO")
    print("=" * 70)

    cache = SemanticCache(max_size=100, similarity_threshold=0.90)

    # 1. Basic cache operations
    print("\n[1] Basic Cache Operations")
    cache.set("What is Python?", "Python is a programming language.", model_id="gpt-4")
    cache.set("Explain Python", "Python is a high-level, interpreted language.", model_id="gpt-4")
    cache.set("What is AI?", "AI is artificial intelligence.", model_id="gpt-4")
    print(f"  Cache size: {len(cache._entries)}")

    # 2. Exact match hit
    print("\n[2] Exact Match Hit")
    result = cache.get("What is Python?", model_id="gpt-4")
    print(f"  Exact hit: {result[:50] if result else 'MISS'}")

    # 3. Semantic similarity hit
    print("\n[3] Semantic Similarity Hit")
    result = cache.get("Tell me about Python programming", model_id="gpt-4")
    print(f"  Semantic hit: {result[:50] if result else 'MISS'}")
    result = cache.get("What is artificial intelligence?", model_id="gpt-4")
    print(f"  Semantic hit (AI): {result[:50] if result else 'MISS'}")

    # 4. Miss
    print("\n[4] Cache Miss")
    result = cache.get("What is quantum computing?", model_id="gpt-4")
    print(f"  Miss: {'MISS' if result is None else 'HIT'}")

    # 5. Model isolation
    print("\n[5] Model Isolation")
    cache.set("Hello", "Hi there!", model_id="gpt-3.5")
    result = cache.get("Hello", model_id="gpt-4")
    print(f"  gpt-4 cache for 'Hello': {result[:50] if result else 'MISS (model isolation)'}")
    result = cache.get("Hello", model_id="gpt-3.5")
    print(f"  gpt-3.5 cache for 'Hello': {result[:50] if result else 'MISS'}")

    # 6. Stats
    print("\n[6] Cache Stats")
    stats = cache.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # 7. Multi-tier cache
    print("\n[7] Multi-Tier Cache")
    mt = MultiTierCache(l1_size=10, l2_size=100, similarity_threshold=0.90)
    mt.set("Q1", "A1", tier=CacheTier.DISK)
    mt.set("Q2", "A2", tier=CacheTier.MEMORY)
    r1 = mt.get("Q2")
    r2 = mt.get("Q1")
    print(f"  L1 hit (Q2): {'✅' if r1 else '❌'}")
    print(f"  L2 hit (Q1): {'✅' if r2 else '❌'}")
    # Q1 should now be promoted to L1
    r3 = mt.get("Q1")
    print(f"  L1 hit after promotion (Q1): {'✅' if r3 else '❌'}")
    mt_stats = mt.get_stats()
    print(f"  Overall hit rate: {mt_stats['overall_hit_rate']:.1%}")

    # 8. TTL expiration
    print("\n[8] TTL Expiration")
    cache_short = SemanticCache(max_size=10, default_ttl=0.01)
    cache_short.set("temp", "temporary value")
    print(f"  Before expiry: {cache_short.get('temp')}")
    time.sleep(0.02)
    print(f"  After expiry: {cache_short.get('temp')}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
