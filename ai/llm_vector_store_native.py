"""Vector Store — In-memory vector similarity search dengan cosine/dot-product distance.

Modul ini menyediakan:
- VectorStore untuk index dan search vector embeddings
- Distance metrics: cosine, dot-product, euclidean
- Metadata filtering pada search results
- Batch insert dan delete
- K-NN search dengan efisiensi O(n)

Arsitektur: VectorEmbedding → VectorIndex → Query → Results
"""

from __future__ import annotations

import json
import time
import uuid
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class DistanceMetric(Enum):
    COSINE = auto()
    DOT_PRODUCT = auto()
    EUCLIDEAN = auto()


@dataclass
class VectorEmbedding:
    """Single vector embedding dengan metadata."""
    id: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    text: str = ""  # Source text jika RAG


@dataclass
class SearchResult:
    """Hasil search dari vector store."""
    id: str
    score: float
    metadata: Dict[str, Any]
    text: str
    distance: float


class VectorIndex:
    """In-memory vector index dengan multiple distance metrics."""

    def __init__(self, dim: int, metric: DistanceMetric = DistanceMetric.COSINE):
        self.dim = dim
        self.metric = metric
        self._vectors: Dict[str, VectorEmbedding] = {}

    def _normalize(self, vec: List[float]) -> List[float]:
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0:
            return vec
        return [x / norm for x in vec]

    def _distance(self, a: List[float], b: List[float]) -> float:
        if self.metric == DistanceMetric.COSINE:
            # Cosine similarity = dot product of normalized vectors
            na = self._normalize(a)
            nb = self._normalize(b)
            return sum(x * y for x, y in zip(na, nb))
        elif self.metric == DistanceMetric.DOT_PRODUCT:
            return sum(x * y for x, y in zip(a, b))
        elif self.metric == DistanceMetric.EUCLIDEAN:
            return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        return 0.0

    def add(self, embedding: VectorEmbedding) -> bool:
        if len(embedding.vector) != self.dim:
            return False
        self._vectors[embedding.id] = embedding
        return True

    def add_batch(self, embeddings: List[VectorEmbedding]) -> Tuple[int, int]:
        added = 0
        rejected = 0
        for e in embeddings:
            if self.add(e):
                added += 1
            else:
                rejected += 1
        return added, rejected

    def delete(self, id: str) -> bool:
        return self._vectors.pop(id, None) is not None

    def get(self, id: str) -> Optional[VectorEmbedding]:
        return self._vectors.get(id)

    def search(self, query: List[float], k: int = 5, filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None) -> List[SearchResult]:
        if len(query) != self.dim:
            return []
        results = []
        for emb in self._vectors.values():
            if filter_fn and not filter_fn(emb.metadata):
                continue
            score = self._distance(query, emb.vector)
            # For cosine and dot, higher is better. For euclidean, lower is better.
            if self.metric == DistanceMetric.EUCLIDEAN:
                results.append((emb.id, score, emb))  # score is distance
            else:
                results.append((emb.id, score, emb))
        # Sort
        if self.metric == DistanceMetric.EUCLIDEAN:
            results.sort(key=lambda x: x[1])  # ascending for distance
        else:
            results.sort(key=lambda x: x[1], reverse=True)  # descending for similarity
        top = results[:k]
        return [SearchResult(
            id=rid,
            score=round(score, 4),
            metadata=emb.metadata,
            text=emb.text,
            distance=round(score, 4) if self.metric == DistanceMetric.EUCLIDEAN else round(1 - score, 4)
        ) for rid, score, emb in top]

    def count(self) -> int:
        return len(self._vectors)

    def clear(self) -> None:
        self._vectors.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "count": len(self._vectors),
            "dimension": self.dim,
            "metric": self.metric.name,
            "avg_vector_norm": round(sum(math.sqrt(sum(x*x for x in e.vector)) for e in self._vectors.values()) / max(len(self._vectors), 1), 2)
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "dim": self.dim,
                "metric": self.metric.name,
                "vectors": {
                    e.id: {
                        "vector": e.vector,
                        "metadata": e.metadata,
                        "text": e.text,
                        "timestamp": e.timestamp
                    }
                    for e in self._vectors.values()
                }
            }, f, indent=2)

    def import_data(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.dim = data.get("dim", self.dim)
        self.metric = DistanceMetric[data.get("metric", "COSINE")]
        for vid, vdata in data.get("vectors", {}).items():
            self._vectors[vid] = VectorEmbedding(
                id=vid,
                vector=vdata["vector"],
                metadata=vdata.get("metadata", {}),
                text=vdata.get("text", ""),
                timestamp=vdata.get("timestamp", time.time())
            )


class SimpleEmbedder:
    """Simple embedding generator untuk demo (bukan production)."""

    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        # Simple hash-based embedding untuk demo
        import hashlib
        h = hashlib.md5(text.encode()).hexdigest()
        vec = []
        for i in range(self.dim):
            # Use chunks of hash as seeds
            seed = int(h[i % 32 : i % 32 + 4], 16) + i * 1000
            vec.append((seed % 2000) / 1000 - 1.0)  # -1 to 1
        # Normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


class RAGPipeline:
    """Simple RAG pipeline: query → embed → search → rerank → context."""

    def __init__(self, store: VectorIndex, embedder: SimpleEmbedder):
        self.store = store
        self.embedder = embedder

    def ingest(self, documents: List[Tuple[str, Dict[str, Any]]]) -> List[str]:
        """documents: (text, metadata)"""
        ids = []
        for text, meta in documents:
            vec = self.embedder.embed(text)
            emb = VectorEmbedding(
                id=str(uuid.uuid4())[:12],
                vector=vec,
                metadata=meta,
                text=text
            )
            self.store.add(emb)
            ids.append(emb.id)
        return ids

    def query(self, question: str, k: int = 3) -> List[SearchResult]:
        q_vec = self.embedder.embed(question)
        return self.store.search(q_vec, k=k)

    def query_with_context(self, question: str, k: int = 3) -> Tuple[List[SearchResult], str]:
        results = self.query(question, k)
        context = "\n\n".join([f"[{i+1}] {r.text}" for i, r in enumerate(results)])
        return results, context


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("VECTOR STORE DEMO")
    print("=" * 70)

    embedder = SimpleEmbedder(dim=64)

    # 1. Basic vector store
    print("\n[1] Basic Vector Store (Cosine)")
    store = VectorIndex(dim=64, metric=DistanceMetric.COSINE)
    docs = [
        ("Python is a versatile programming language used for web, data, and AI.", {"topic": "python", "category": "programming"}),
        ("JavaScript runs in browsers and powers modern web applications.", {"topic": "javascript", "category": "programming"}),
        ("Machine learning uses algorithms to learn patterns from data.", {"topic": "ml", "category": "ai"}),
        ("Deep learning is a subset of machine learning with neural networks.", {"topic": "dl", "category": "ai"}),
        ("Data science combines statistics, programming, and domain knowledge.", {"topic": "data-science", "category": "data"}),
    ]
    for text, meta in docs:
        emb = VectorEmbedding(str(uuid.uuid4())[:8], embedder.embed(text), metadata=meta, text=text)
        store.add(emb)
    print(f"  Added {store.count()} vectors")

    # Search
    query = embedder.embed("What programming language is good for AI?")
    results = store.search(query, k=3)
    print(f"  Query: 'What programming language is good for AI?'")
    for r in results:
        print(f"    [{r.score:.3f}] {r.text[:60]}... (topic: {r.metadata.get('topic')})")

    # 2. With filter
    print("\n[2] Search with Metadata Filter")
    results = store.search(query, k=3, filter_fn=lambda m: m.get("category") == "ai")
    print(f"  Filtered to AI category:")
    for r in results:
        print(f"    [{r.score:.3f}] {r.text[:60]}...")

    # 3. Different distance metrics
    print("\n[3] Distance Metrics Comparison")
    for metric in [DistanceMetric.COSINE, DistanceMetric.DOT_PRODUCT, DistanceMetric.EUCLIDEAN]:
        mstore = VectorIndex(dim=64, metric=metric)
        for text, meta in docs:
            mstore.add(VectorEmbedding(str(uuid.uuid4())[:8], embedder.embed(text), metadata=meta, text=text))
        r = mstore.search(query, k=1)[0]
        print(f"  {metric.name}: top score={r.score:.3f}, text='{r.text[:50]}...'")

    # 4. RAG Pipeline
    print("\n[4] RAG Pipeline")
    rag = RAGPipeline(VectorIndex(dim=64, metric=DistanceMetric.COSINE), embedder)
    rag.ingest(docs)
    results, context = rag.query_with_context("Tell me about neural networks", k=2)
    print(f"  Results:")
    for r in results:
        print(f"    [{r.score:.3f}] {r.text[:70]}...")
    print(f"  Context:\n{context}")

    # 5. Batch operations
    print("\n[5] Batch Operations")
    batch_store = VectorIndex(dim=64)
    batch = [VectorEmbedding(str(i), embedder.embed(f"Document {i} about topic {i%3}")) for i in range(100)]
    added, rejected = batch_store.add_batch(batch)
    print(f"  Added {added}, rejected {rejected}")
    print(f"  Stats: {batch_store.get_stats()}")

    # 6. Export/Import
    print("\n[6] Export/Import")
    store.export("/tmp/vector_store.json")
    print(f"  Exported to /tmp/vector_store.json")
    new_store = VectorIndex(dim=64)
    new_store.import_data("/tmp/vector_store.json")
    print(f"  Imported {new_store.count()} vectors")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
