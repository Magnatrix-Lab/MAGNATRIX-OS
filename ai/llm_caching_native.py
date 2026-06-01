"""Semantic Caching Engine — Embedding-based cache, deduplication, TTL.

Modul ini menyediakan:
- SemanticCache dengan similarity-based lookup
- CacheEntry untuk menyimpan response dengan metadata
- TTLManager untuk expiration dan cleanup
- CacheStats untuk metrics dan hit rate tracking
- DeduplicationEngine untuk exact match deduplication

Arsitektur: Query → Normalize → Embed → Lookup → (Hit: Return / Miss: Execute → Store)
"""

from __future__ import annotations

import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class CachePolicy(Enum):
    LRU = auto()
    LFU = auto()
    FIFO = auto()
    TTL = auto()


@dataclass
class CacheEntry:
    """Single cached response entry."""
    key: str
    query: str
    response: Any
    embedding: Optional[List[float]] = None
    timestamp: float = field(default_factory=time.time)
    ttl: float = 3600.0
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl

    def touch(self) -> None:
        self.access_count += 1
        self.last_accessed = time.time()


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    insertions: int = 0
    exact_hits: int = 0
    semantic_hits: int = 0
    total_queries: int = 0
    bytes_stored: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def exact_hit_rate(self) -> float:
        total = self.total_queries
        return self.exact_hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": round(self.hit_rate, 4),
            "exact_hit_rate": round(self.exact_hit_rate, 4),
            "total_entries": self.insertions - self.evictions,
            "bytes_stored": self.bytes_stored,
        }


class EmbeddingSimulator:
    """Simulate embeddings for semantic similarity (real impl would use real embedder)."""

    @staticmethod
    def embed(text: str) -> List[float]:
        # Simple hash-based embedding simulation
        h = hashlib.sha256(text.encode()).hexdigest()
        vec = [int(h[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
        return vec

    @staticmethod
    def similarity(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class SemanticCache:
    """Cache with semantic similarity lookup."""

    def __init__(self, max_size: int = 1000, similarity_threshold: float = 0.85, policy: CachePolicy = CachePolicy.LRU):
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.policy = policy
        self._entries: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._embedder = EmbeddingSimulator()

    def _make_key(self, query: str) -> str:
        return hashlib.sha256(query.encode()).hexdigest()[:16]

    def get(self, query: str) -> Optional[CacheEntry]:
        self._stats.total_queries += 1
        key = self._make_key(query)

        # Exact match
        entry = self._entries.get(key)
        if entry and not entry.is_expired():
            entry.touch()
            self._stats.hits += 1
            self._stats.exact_hits += 1
            return entry

        # Semantic match
        if entry:
            self._evict(key)  # Expired exact match

        query_emb = self._embedder.embed(query)
        best_match = None
        best_score = 0.0

        for e in self._entries.values():
            if e.is_expired():
                continue
            if e.embedding is None:
                continue
            score = self._embedder.similarity(query_emb, e.embedding)
            if score > best_score and score >= self.similarity_threshold:
                best_score = score
                best_match = e

        if best_match:
            best_match.touch()
            self._stats.hits += 1
            self._stats.semantic_hits += 1
            return best_match

        self._stats.misses += 1
        return None

    def put(self, query: str, response: Any, ttl: float = 3600.0, tags: Optional[List[str]] = None) -> CacheEntry:
        key = self._make_key(query)

        # Evict if needed
        if len(self._entries) >= self.max_size:
            self._evict_by_policy()

        embedding = self._embedder.embed(query)
        entry = CacheEntry(
            key=key,
            query=query,
            response=response,
            embedding=embedding,
            ttl=ttl,
            tags=tags or []
        )
        self._entries[key] = entry
        self._stats.insertions += 1
        self._stats.bytes_stored += len(str(response).encode())
        return entry

    def invalidate(self, key: str) -> bool:
        entry = self._entries.pop(key, None)
        if entry:
            self._stats.bytes_stored -= len(str(entry.response).encode())
            return True
        return False

    def invalidate_by_tag(self, tag: str) -> int:
        to_remove = [k for k, e in self._entries.items() if tag in e.tags]
        for k in to_remove:
            self.invalidate(k)
        return len(to_remove)

    def _evict(self, key: str) -> None:
        entry = self._entries.pop(key, None)
        if entry:
            self._stats.evictions += 1
            self._stats.bytes_stored -= len(str(entry.response).encode())

    def _evict_by_policy(self) -> None:
        if not self._entries:
            return
        if self.policy == CachePolicy.LRU:
            oldest = min(self._entries.values(), key=lambda e: e.last_accessed)
            self._evict(oldest.key)
        elif self.policy == CachePolicy.LFU:
            least = min(self._entries.values(), key=lambda e: e.access_count)
            self._evict(least.key)
        elif self.policy == CachePolicy.FIFO:
            oldest = min(self._entries.values(), key=lambda e: e.timestamp)
            self._evict(oldest.key)
        else:
            self._evict(next(iter(self._entries.keys())))

    def cleanup_expired(self) -> int:
        expired = [k for k, e in self._entries.items() if e.is_expired()]
        for k in expired:
            self._evict(k)
        return len(expired)

    def get_stats(self) -> CacheStats:
        return self._stats

    def clear(self) -> None:
        self._entries.clear()
        self._stats = CacheStats()

    def size(self) -> int:
        return len(self._entries)

    def export(self, path: str) -> None:
        data = {
            "stats": self._stats.to_dict(),
            "entries": [
                {
                    "key": e.key,
                    "query": e.query[:100],
                    "access_count": e.access_count,
                    "timestamp": e.timestamp,
                    "tags": e.tags
                }
                for e in self._entries.values()
            ]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


class DeduplicationEngine:
    """Exact and near-exact deduplication."""

    def __init__(self, similarity_threshold: float = 0.95):
        self.similarity_threshold = similarity_threshold
        self._seen: Dict[str, str] = {}  # hash -> original query
        self._embedder = EmbeddingSimulator()

    def is_duplicate(self, query: str) -> Optional[str]:
        h = hashlib.sha256(query.encode()).hexdigest()[:16]
        if h in self._seen:
            return self._seen[h]

        # Near-duplicate check
        emb = self._embedder.embed(query)
        for orig, orig_emb in self._get_embeddings():
            if self._embedder.similarity(emb, orig_emb) >= self.similarity_threshold:
                return orig
        return None

    def add(self, query: str) -> None:
        h = hashlib.sha256(query.encode()).hexdigest()[:16]
        self._seen[h] = query

    def _get_embeddings(self) -> List[Tuple[str, List[float]]]:
        return [(q, self._embedder.embed(q)) for q in self._seen.values()]

    def deduplicate_batch(self, queries: List[str]) -> Tuple[List[str], Dict[str, str]]:
        unique = []
        duplicates = {}
        for q in queries:
            dup = self.is_duplicate(q)
            if dup:
                duplicates[q] = dup
            else:
                self.add(q)
                unique.append(q)
        return unique, duplicates


class MultiTierCache:
    """L1 (memory) + L2 (disk) two-tier cache."""

    def __init__(self, l1_size: int = 500, l2_size: int = 5000, l2_path: str = "./cache_l2.json"):
        self.l1 = SemanticCache(max_size=l1_size, similarity_threshold=0.90)
        self.l2 = SemanticCache(max_size=l2_size, similarity_threshold=0.85)
        self.l2_path = l2_path

    def get(self, query: str) -> Optional[CacheEntry]:
        # Try L1 first
        entry = self.l1.get(query)
        if entry:
            return entry
        # Try L2, promote if found
        entry = self.l2.get(query)
        if entry:
            self.l1.put(query, entry.response, ttl=entry.ttl, tags=entry.tags)
            return entry
        return None

    def put(self, query: str, response: Any, ttl: float = 3600.0, tags: Optional[List[str]] = None) -> None:
        self.l1.put(query, response, ttl, tags)
        self.l2.put(query, response, ttl, tags)

    def invalidate(self, query: str) -> None:
        key = self.l1._make_key(query)
        self.l1.invalidate(key)
        self.l2.invalidate(key)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "l1": self.l1.get_stats().to_dict(),
            "l2": self.l2.get_stats().to_dict(),
        }

    def save_l2(self) -> None:
        self.l2.export(self.l2_path)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("SEMANTIC CACHING ENGINE DEMO")
    print("=" * 70)

    # 1. Basic cache operations
    print("\n[1] Basic Cache Operations")
    cache = SemanticCache(max_size=100, similarity_threshold=0.85)
    cache.put("What is Python?", "Python is a programming language.", ttl=300)
    cache.put("Explain Python", "Python is a high-level programming language.", ttl=300)
    cache.put("How to write Python?", "Use a text editor and Python interpreter.", ttl=300)
    print(f"  Cache size: {cache.size()}")

    # 2. Exact hit
    print("\n[2] Exact Hit")
    entry = cache.get("What is Python?")
    print(f"  Exact hit: {entry is not None}")
    if entry:
        print(f"  Response: {entry.response[:50]}...")

    # 3. Semantic hit
    print("\n[3] Semantic Hit")
    entry = cache.get("What is Python programming language?")
    print(f"  Semantic hit: {entry is not None}")
    if entry:
        print(f"  Matched query: {entry.query[:50]}...")
        print(f"  Access count: {entry.access_count}")

    # 4. Miss
    print("\n[4] Cache Miss")
    entry = cache.get("How to cook pasta?")
    print(f"  Miss: {entry is None}")

    # 5. Stats
    print("\n[5] Cache Stats")
    stats = cache.get_stats()
    print(f"  Stats: {stats.to_dict()}")

    # 6. TTL expiration
    print("\n[6] TTL Expiration")
    cache.put("Temp query", "Temp response", ttl=0.01)
    time.sleep(0.05)
    cache.cleanup_expired()
    print(f"  After cleanup: {cache.size()} entries")

    # 7. Eviction policy
    print("\n[7] Eviction Policy (LRU)")
    small_cache = SemanticCache(max_size=3, policy=CachePolicy.LRU)
    small_cache.put("A", "Response A")
    small_cache.put("B", "Response B")
    small_cache.put("C", "Response C")
    small_cache.get("A")  # Touch A
    small_cache.put("D", "Response D")  # Should evict B or C
    print(f"  Size after eviction: {small_cache.size()}")

    # 8. Deduplication
    print("\n[8] Deduplication Engine")
    dedup = DeduplicationEngine()
    queries = [
        "What is Python?",
        "What is Python?",  # Exact duplicate
        "Tell me about Python",  # Near duplicate
        "How to learn Java?",
    ]
    unique, duplicates = dedup.deduplicate_batch(queries)
    print(f"  Unique: {len(unique)}, Duplicates: {len(duplicates)}")
    for q, orig in duplicates.items():
        print(f"    '{q}' -> duplicate of '{orig}'")

    # 9. Multi-tier cache
    print("\n[9] Multi-Tier Cache")
    multi = MultiTierCache(l1_size=10, l2_size=100)
    multi.put("Query 1", "Response 1")
    multi.put("Query 2", "Response 2")
    entry = multi.get("Query 1")
    print(f"  L1+L2 hit: {entry is not None}")
    print(f"  L1 size: {multi.l1.size()}, L2 size: {multi.l2.size()}")
    print(f"  Stats: {multi.get_stats()}")

    # 10. Tag invalidation
    print("\n[10] Tag Invalidation")
    cache.put("Q1", "R1", tags=["temp"])
    cache.put("Q2", "R2", tags=["temp"])
    cache.put("Q3", "R3", tags=["permanent"])
    removed = cache.invalidate_by_tag("temp")
    print(f"  Removed {removed} entries with tag 'temp'")
    print(f"  Remaining: {cache.size()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
