"""Semantic Cache — Cache LLM responses by embedding similarity, TTL, and hit tracking.

Modul ini menyediakan:
- SemanticCache dengan similarity-based lookup (bukan exact match)
- TTL-based expiration dengan automatic cleanup
- Hit/miss tracking dan cache statistics
- Cache warming dan preloading
- Configurable similarity threshold dan max size
"""

from __future__ import annotations

import json
import time
import uuid
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class CachePolicy(Enum):
    LRU = auto()
    LFU = auto()
    FIFO = auto()
    TTL_ONLY = auto()


@dataclass
class CacheEntry:
    """Single cache entry dengan embedding dan metadata."""
    key: str
    query_embedding: List[float]
    query_text: str
    response: str
    timestamp: float
    ttl: float = 3600.0  # seconds
    hits: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl

    def remaining_ttl(self) -> float:
        return max(0, self.ttl - (time.time() - self.timestamp))


class SemanticCache:
    """Cache responses berdasarkan semantic similarity dari query embeddings."""

    def __init__(self, similarity_threshold: float = 0.85, max_size: int = 1000, policy: CachePolicy = CachePolicy.LRU):
        self.threshold = similarity_threshold
        self.max_size = max_size
        self.policy = policy
        self._entries: Dict[str, CacheEntry] = {}
        self._access_times: Dict[str, float] = {}
        self._hit_count: Dict[str, int] = {}
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "inserts": 0}

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def get(self, query_embedding: List[float], query_text: str = "") -> Optional[str]:
        """Lookup cache berdasarkan similarity."""
        best_match = None
        best_score = 0.0
        for entry in self._entries.values():
            if entry.is_expired():
                continue
            score = self._cosine_similarity(query_embedding, entry.query_embedding)
            if score > best_score and score >= self.threshold:
                best_score = score
                best_match = entry
        if best_match:
            best_match.hits += 1
            self._hit_count[best_match.key] = self._hit_count.get(best_match.key, 0) + 1
            self._access_times[best_match.key] = time.time()
            self._stats["hits"] += 1
            return best_match.response
        self._stats["misses"] += 1
        return None

    def put(self, query_embedding: List[float], query_text: str, response: str, ttl: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add entry to cache."""
        key = str(uuid.uuid4())[:12]
        entry = CacheEntry(
            key=key,
            query_embedding=query_embedding,
            query_text=query_text,
            response=response,
            timestamp=time.time(),
            ttl=ttl or 3600.0,
            metadata=metadata or {}
        )
        # Evict if at capacity
        if len(self._entries) >= self.max_size:
            self._evict()
        self._entries[key] = entry
        self._access_times[key] = time.time()
        self._hit_count[key] = 0
        self._stats["inserts"] += 1
        return key

    def _evict(self) -> None:
        if not self._entries:
            return
        if self.policy == CachePolicy.LRU:
            oldest = min(self._entries.keys(), key=lambda k: self._access_times.get(k, 0))
        elif self.policy == CachePolicy.LFU:
            oldest = min(self._entries.keys(), key=lambda k: self._hit_count.get(k, 0))
        elif self.policy == CachePolicy.FIFO:
            oldest = min(self._entries.keys(), key=lambda k: self._entries[k].timestamp)
        else:  # TTL_ONLY
            oldest = min(self._entries.keys(), key=lambda k: self._entries[k].remaining_ttl())
        self._entries.pop(oldest, None)
        self._access_times.pop(oldest, None)
        self._hit_count.pop(oldest, None)
        self._stats["evictions"] += 1

    def invalidate(self, key: str) -> bool:
        if key in self._entries:
            self._entries.pop(key, None)
            self._access_times.pop(key, None)
            self._hit_count.pop(key, None)
            return True
        return False

    def invalidate_by_similarity(self, query_embedding: List[float], threshold: Optional[float] = None) -> int:
        thresh = threshold or self.threshold
        removed = 0
        for key, entry in list(self._entries.items()):
            if self._cosine_similarity(query_embedding, entry.query_embedding) >= thresh:
                self.invalidate(key)
                removed += 1
        return removed

    def clear_expired(self) -> int:
        expired = [k for k, e in self._entries.items() if e.is_expired()]
        for k in expired:
            self.invalidate(k)
        return len(expired)

    def clear(self) -> None:
        self._entries.clear()
        self._access_times.clear()
        self._hit_count.clear()

    def get_stats(self) -> Dict[str, Any]:
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / max(total_requests, 1)
        return {
            "size": len(self._entries),
            "max_size": self.max_size,
            "threshold": self.threshold,
            "policy": self.policy.name,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": round(hit_rate, 3),
            "evictions": self._stats["evictions"],
            "inserts": self._stats["inserts"],
            "expired_entries": sum(1 for e in self._entries.values() if e.is_expired())
        }

    def list_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [
            {
                "key": e.key,
                "query_text": e.query_text[:100],
                "hits": e.hits,
                "remaining_ttl": round(e.remaining_ttl(), 1),
                "expired": e.is_expired()
            }
            for e in sorted(self._entries.values(), key=lambda x: x.hits, reverse=True)[:limit]
        ]

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "threshold": self.threshold,
                "max_size": self.max_size,
                "policy": self.policy.name,
                "stats": self._stats,
                "entries": {
                    e.key: {
                        "query_text": e.query_text,
                        "response": e.response[:200],
                        "query_embedding": e.query_embedding[:8],  # Truncate for export
                        "timestamp": e.timestamp,
                        "ttl": e.ttl,
                        "hits": e.hits
                    }
                    for e in self._entries.values()
                }
            }, f, indent=2)


class CacheWarming:
    """Preload cache dengan common queries."""

    def __init__(self, cache: SemanticCache, embed_fn: Callable[[str], List[float]]):
        self.cache = cache
        self.embed_fn = embed_fn

    def preload(self, common_queries: List[Tuple[str, str, Optional[float]]]) -> int:
        """(query_text, response, ttl)"""
        added = 0
        for query, response, ttl in common_queries:
            emb = self.embed_fn(query)
            self.cache.put(emb, query, response, ttl=ttl)
            added += 1
        return added

    def preload_from_file(self, path: str) -> int:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("items", [])
        added = 0
        for item in items:
            query = item.get("query", "")
            response = item.get("response", "")
            ttl = item.get("ttl")
            emb = self.embed_fn(query)
            self.cache.put(emb, query, response, ttl=ttl)
            added += 1
        return added


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("SEMANTIC CACHE DEMO")
    print("=" * 70)

    # Simple embedder for demo
    def embed(text: str) -> List[float]:
        import hashlib
        h = hashlib.md5(text.encode()).hexdigest()
        vec = []
        for i in range(32):
            seed = int(h[i:i+2], 16) + ord(text[i % len(text)]) if text else 0
            vec.append((seed % 200) / 100 - 1.0)
        norm = math.sqrt(sum(x*x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    cache = SemanticCache(similarity_threshold=0.85, max_size=50, policy=CachePolicy.LRU)

    # 1. Basic cache operations
    print("\n[1] Basic Cache Operations")
    q1 = "What is Python?"
    emb1 = embed(q1)
    r1 = cache.get(emb1, q1)
    print(f"  First query '{q1}': {'HIT' if r1 else 'MISS'}")

    cache.put(emb1, q1, "Python is a programming language.")
    r2 = cache.get(emb1, q1)
    print(f"  Second query '{q1}': {'HIT' if r2 else 'MISS'} -> {r2}")

    # 2. Semantic similarity
    print("\n[2] Semantic Similarity")
    similar_queries = [
        "Tell me about Python",
        "What is the Python language?",
        "Explain Python programming",
        "How does JavaScript work?",  # Different topic
    ]
    for q in similar_queries:
        emb = embed(q)
        result = cache.get(emb, q)
        status = "HIT" if result else "MISS"
        print(f"  '{q}': {status}")

    # 3. Put more entries
    print("\n[3] Multiple Entries")
    entries = [
        ("What is AI?", "AI stands for Artificial Intelligence."),
        ("Explain machine learning", "ML is a subset of AI."),
        ("What is deep learning?", "DL uses neural networks."),
        ("Tell me about data science", "DS combines stats and coding."),
    ]
    for q, r in entries:
        cache.put(embed(q), q, r, ttl=300)
    print(f"  Cache size: {cache.get_stats()['size']}")

    # 4. Cache policy comparison
    print("\n[4] Cache Policy Comparison")
    for policy in [CachePolicy.LRU, CachePolicy.LFU, CachePolicy.FIFO]:
        c = SemanticCache(similarity_threshold=0.85, max_size=3, policy=policy)
        for i in range(5):
            c.put(embed(f"Query {i}"), f"Query {i}", f"Response {i}")
        # Access some
        for _ in range(3):
            c.get(embed("Query 1"))
        c.get(embed("Query 3"))
        # Add one more to trigger eviction
        c.put(embed("Query 99"), "Query 99", "Response 99")
        print(f"  {policy.name}: {c.get_stats()['size']} entries, hit_rate={c.get_stats()['hit_rate']:.1%}")

    # 5. TTL expiration
    print("\n[5] TTL Expiration")
    ttl_cache = SemanticCache(similarity_threshold=0.85, max_size=10)
    ttl_cache.put(embed("temp"), "temp", "value", ttl=0.1)
    print(f"  Before expiry: {ttl_cache.get(embed('temp'))}")
    time.sleep(0.2)
    ttl_cache.clear_expired()
    print(f"  After expiry: {ttl_cache.get(embed('temp'))}")
    print(f"  Stats: {ttl_cache.get_stats()}")

    # 6. Cache warming
    print("\n[6] Cache Warming")
    warmer = CacheWarming(cache, embed)
    common = [
        ("Hello", "Hello! How can I help you today?", 3600),
        ("What can you do?", "I can answer questions, write code, analyze data, and more.", 3600),
        ("Who are you?", "I am an AI assistant.", 3600),
    ]
    added = warmer.preload(common)
    print(f"  Preloaded {added} entries")
    print(f"  Cache stats: {cache.get_stats()}")

    # 7. Export
    cache.export("/tmp/semantic_cache.json")
    print(f"\n[7] Exported cache to /tmp/semantic_cache.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
