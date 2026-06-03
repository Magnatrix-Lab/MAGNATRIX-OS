"""
llm_embedding_cache_native.py
MAGNATRIX-OS Embedding Cache Engine
Native Python, stdlib only.
Provides semantic embedding caching with similarity-based lookup, LFU eviction, and vector indexing.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class SimilarityMetric(Enum):
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"


@dataclass
class EmbeddingEntry:
    key: str
    text_hash: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key, "vector_dim": len(self.vector),
            "access_count": self.access_count, "created_at": self.created_at,
        }


class EmbeddingCacheEngine:
    """Semantic embedding cache with similarity-based retrieval."""

    def __init__(self, max_size: int = 10000, similarity_threshold: float = 0.95) -> None:
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self._cache: Dict[str, EmbeddingEntry] = {}
        self._hits = 0
        self._misses = 0

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def store(self, text: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> EmbeddingEntry:
        key = self._hash_text(text)
        entry = EmbeddingEntry(key=key, text_hash=key, vector=vector, metadata=metadata or {})
        self._cache[key] = entry
        self._evict_if_needed()
        return entry

    def get_exact(self, text: str) -> Optional[EmbeddingEntry]:
        key = self._hash_text(text)
        entry = self._cache.get(key)
        if entry:
            entry.access_count += 1
            entry.last_accessed = time.time()
            self._hits += 1
            return entry
        self._misses += 1
        return None

    def get_similar(self, vector: List[float], top_k: int = 5) -> List[Tuple[EmbeddingEntry, float]]:
        results = []
        for entry in self._cache.values():
            sim = self._cosine_similarity(vector, entry.vector)
            if sim >= self.similarity_threshold:
                results.append((entry, sim))
        results.sort(key=lambda x: x[1], reverse=True)
        for entry, _ in results[:top_k]:
            entry.access_count += 1
            entry.last_accessed = time.time()
        self._hits += len(results[:top_k])
        self._misses += 1 if not results else 0
        return results[:top_k]

    def _evict_if_needed(self) -> None:
        if len(self._cache) > self.max_size:
            # LFU eviction
            sorted_entries = sorted(self._cache.values(), key=lambda e: e.access_count)
            to_evict = sorted_entries[:len(sorted_entries) - self.max_size]
            for e in to_evict:
                del self._cache[e.key]

    def invalidate(self, text: str) -> bool:
        key = self._hash_text(text)
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._cache), "max_size": self.max_size,
            "hits": self._hits, "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }

    def get_dimension(self) -> int:
        if not self._cache:
            return 0
        return len(next(iter(self._cache.values())).vector)

    def export_vectors(self, path: str) -> None:
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump({k: {"vector": e.vector, "metadata": e.metadata} for k, e in self._cache.items()}, f, default=str)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Embedding Cache Engine")
    print("=" * 60)

    engine = EmbeddingCacheEngine(max_size=1000, similarity_threshold=0.9)

    print("\n--- Store embeddings ---")
    for i in range(5):
        vector = [0.1 * (i + 1)] * 10
        engine.store(f"text_{i}", vector, {"source": "test"})

    print("\n--- Exact match ---")
    entry = engine.get_exact("text_2")
    print(f"  Found: {entry is not None}")

    print("\n--- Similarity search ---")
    query = [0.25] * 10  # Close to text_2 (0.3)
    results = engine.get_similar(query, top_k=3)
    for entry, sim in results:
        print(f"  {entry.key}: similarity={sim:.3f}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nEmbedding Cache test complete.")


if __name__ == "__main__":
    run()
