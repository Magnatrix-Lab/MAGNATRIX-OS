"""Embedding Engine — Text embedding generation, normalization, and similarity computation.

Modul ini menyediakan:
- Embedder untuk generate embeddings dari text
- EmbeddingNormalizer untuk normalize dan quantize embeddings
- SimilarityEngine untuk cosine/dot-product similarity
- EmbeddingCache untuk caching frequently used embeddings
- EmbeddingPipeline untuk end-to-end embedding workflow
"""

from __future__ import annotations

import json
import time
import uuid
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


@dataclass
class Embedding:
    """Single embedding vector."""
    embedding_id: str
    text: str
    vector: List[float]
    model: str = "default"
    dimension: int = 0
    normalized: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.dimension == 0 and self.vector:
            self.dimension = len(self.vector)


class Embedder:
    """Generate embeddings from text."""

    def __init__(self, dimension: int = 384, model: str = "sim-default"):
        self.dimension = dimension
        self.model = model

    def embed(self, text: str, embed_fn: Optional[Callable[[str], List[float]]] = None) -> Embedding:
        embed_fn = embed_fn or self._default_embed
        vector = embed_fn(text)
        return Embedding(
            embedding_id=str(uuid.uuid4())[:12],
            text=text[:500],
            vector=vector[:self.dimension],
            model=self.model,
            dimension=self.dimension,
        )

    def embed_batch(self, texts: List[str], embed_fn: Optional[Callable[[str], List[float]]] = None) -> List[Embedding]:
        return [self.embed(t, embed_fn) for t in texts]

    def _default_embed(self, text: str) -> List[float]:
        # Deterministic simulated embedding from text hash
        import random
        seed = sum(ord(c) for c in text[:100]) % 100000
        random.seed(seed)
        return [random.uniform(-1, 1) for _ in range(self.dimension)]


class EmbeddingNormalizer:
    """Normalize and quantize embeddings."""

    @staticmethod
    def normalize(emb: Embedding) -> Embedding:
        vec = emb.vector
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0:
            return emb
        normalized = [x / norm for x in vec]
        return Embedding(
            embedding_id=emb.embedding_id,
            text=emb.text,
            vector=normalized,
            model=emb.model,
            dimension=emb.dimension,
            normalized=True,
            metadata={**emb.metadata, "original_norm": round(norm, 4)},
        )

    @staticmethod
    def quantize_int8(emb: Embedding) -> Embedding:
        max_val = max(abs(x) for x in emb.vector) or 1.0
        scaled = [int(x / max_val * 127) for x in emb.vector]
        return Embedding(
            embedding_id=emb.embedding_id,
            text=emb.text,
            vector=scaled,
            model=emb.model,
            dimension=emb.dimension,
            normalized=emb.normalized,
            metadata={**emb.metadata, "quantized": "int8"},
        )

    @staticmethod
    def binary_quantize(emb: Embedding) -> Embedding:
        binary = [1 if x > 0 else 0 for x in emb.vector]
        return Embedding(
            embedding_id=emb.embedding_id,
            text=emb.text,
            vector=binary,
            model=emb.model,
            dimension=emb.dimension,
            normalized=emb.normalized,
            metadata={**emb.metadata, "quantized": "binary"},
        )


class SimilarityEngine:
    """Compute similarities between embeddings."""

    @staticmethod
    def cosine(a: Embedding, b: Embedding) -> float:
        vec_a = a.vector
        vec_b = b.vector
        if len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(x * y for x, y in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(x * x for x in vec_a)) or 1.0
        norm_b = math.sqrt(sum(x * x for x in vec_b)) or 1.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def dot_product(a: Embedding, b: Embedding) -> float:
        return sum(x * y for x, y in zip(a.vector, b.vector))

    @staticmethod
    def euclidean(a: Embedding, b: Embedding) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a.vector, b.vector)))

    @staticmethod
    def hamming(a: Embedding, b: Embedding) -> float:
        if len(a.vector) != len(b.vector):
            return 0.0
        matches = sum(1 for x, y in zip(a.vector, b.vector) if x == y)
        return matches / len(a.vector)

    def search(self, query: Embedding, candidates: List[Embedding], top_k: int = 5, metric: str = "cosine") -> List[Tuple[Embedding, float]]:
        metrics = {
            "cosine": self.cosine,
            "dot": self.dot_product,
            "euclidean": self.euclidean,
            "hamming": self.hamming,
        }
        fn = metrics.get(metric, self.cosine)
        scored = [(c, fn(query, c)) for c in candidates]
        if metric == "euclidean":
            scored.sort(key=lambda x: x[1])
        else:
            scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


class EmbeddingCache:
    """Cache embeddings for frequently used texts."""

    def __init__(self, max_size: int = 1000, ttl: float = 3600.0):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Tuple[Embedding, float]] = {}  # text_hash -> (embedding, timestamp)

    def _hash(self, text: str) -> str:
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def get(self, text: str) -> Optional[Embedding]:
        h = self._hash(text)
        entry = self._cache.get(h)
        if not entry:
            return None
        emb, ts = entry
        if time.time() - ts > self.ttl:
            del self._cache[h]
            return None
        return emb

    def put(self, text: str, emb: Embedding) -> None:
        h = self._hash(text)
        self._cache[h] = (emb, time.time())
        if len(self._cache) > self.max_size:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
        }


class EmbeddingPipeline:
    """End-to-end embedding workflow."""

    def __init__(self, dimension: int = 384, normalize: bool = True, cache: bool = True):
        self.embedder = Embedder(dimension=dimension)
        self.normalizer = EmbeddingNormalizer()
        self.similarity = SimilarityEngine()
        self.cache = EmbeddingCache() if cache else None
        self.normalize = normalize
        self._history: List[Embedding] = []

    def process(self, text: str) -> Embedding:
        if self.cache:
            cached = self.cache.get(text)
            if cached:
                return cached
        emb = self.embedder.embed(text)
        if self.normalize:
            emb = self.normalizer.normalize(emb)
        if self.cache:
            self.cache.put(text, emb)
        self._history.append(emb)
        return emb

    def process_batch(self, texts: List[str]) -> List[Embedding]:
        return [self.process(t) for t in texts]

    def find_similar(self, query_text: str, top_k: int = 5, metric: str = "cosine") -> List[Tuple[Embedding, float]]:
        query = self.process(query_text)
        return self.similarity.search(query, self._history, top_k, metric)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_embeddings": len(self._history),
            "dimension": self.embedder.dimension,
            "cache": self.cache.get_stats() if self.cache else None,
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([{
                "id": e.embedding_id,
                "text": e.text[:50],
                "dimension": e.dimension,
                "normalized": e.normalized,
            } for e in self._history], f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("EMBEDDING ENGINE DEMO")
    print("=" * 70)

    # 1. Embed text
    print("\n[1] Embed Text")
    embedder = Embedder(dimension=128, model="demo-embed")
    emb1 = embedder.embed("The quick brown fox")
    print(f"  Embedding: {emb1.embedding_id}, dim={emb1.dimension}, model={emb1.model}")
    print(f"  Vector sample: {emb1.vector[:5]}")

    # 2. Batch embed
    print("\n[2] Batch Embed")
    texts = ["Hello world", "Machine learning", "Deep neural networks", "Natural language processing"]
    embs = embedder.embed_batch(texts)
    print(f"  Batch: {len(embs)} embeddings")
    for e in embs:
        print(f"    {e.text[:20]}... dim={e.dimension}")

    # 3. Normalization
    print("\n[3] Normalization")
    norm = EmbeddingNormalizer.normalize(emb1)
    print(f"  Normalized: {norm.normalized}")
    norm_val = math.sqrt(sum(x * x for x in norm.vector))
    print(f"  L2 norm: {norm_val:.4f}")

    # 4. Quantization
    print("\n[4] Quantization")
    int8 = EmbeddingNormalizer.quantize_int8(emb1)
    print(f"  INT8: range [{min(int8.vector)}, {max(int8.vector)}]")
    binary = EmbeddingNormalizer.binary_quantize(emb1)
    print(f"  Binary: {sum(binary.vector)} / {len(binary.vector)} positive bits")

    # 5. Similarity
    print("\n[5] Similarity")
    sim = SimilarityEngine()
    emb_a = embedder.embed("Artificial intelligence")
    emb_b = embedder.embed("Machine learning")
    emb_c = embedder.embed("Baking a cake")
    print(f"  AI vs ML: cosine={sim.cosine(emb_a, emb_b):.4f}")
    print(f"  AI vs Cake: cosine={sim.cosine(emb_a, emb_c):.4f}")
    print(f"  AI vs ML: dot={sim.dot_product(emb_a, emb_b):.4f}")
    print(f"  AI vs ML: euclidean={sim.euclidean(emb_a, emb_b):.4f}")

    # 6. Search
    print("\n[6] Similarity Search")
    pipeline = EmbeddingPipeline(dimension=128, normalize=True)
    for t in texts + ["Computer vision", "Reinforcement learning", "Data science"]:
        pipeline.process(t)
    results = pipeline.find_similar("Machine learning", top_k=3)
    print(f"  Query: 'Machine learning'")
    for emb, score in results:
        print(f"    [{score:.4f}] {emb.text}")

    # 7. Cache
    print("\n[7] Cache")
    print(f"  Cache stats: {pipeline.cache.get_stats()}")
    # Re-process (should hit cache)
    cached = pipeline.process("Machine learning")
    print(f"  Re-process cache hit: {cached.embedding_id == pipeline.cache.get('Machine learning').embedding_id}")

    # 8. Pipeline stats
    print(f"\n[8] Pipeline Stats")
    print(f"  {pipeline.get_stats()}")

    # 9. Export
    print("\n[9] Export")
    pipeline.export("/tmp/embeddings.json")
    print("  Exported to /tmp/embeddings.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
