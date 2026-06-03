#!/usr/bin/env python3
"""
MAGNATRIX-OS — Embedding Engine
ai/llm_embedding_engine_native.py

Features:
- Vector embedding simulation (word/document to vector)
- Cosine similarity scoring between vectors
- K-NN nearest neighbor search (brute force)
- Simple clustering (k-means-like grouping)
- Vector storage and indexing

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("embedding_engine")


@dataclass
class EmbeddingVector:
    id: str
    text: str
    vector: List[float]


@dataclass
class Neighbor:
    id: str
    distance: float
    text: str


class EmbeddingEngine:
    """Vector embedding with similarity and clustering."""

    def __init__(self, dim: int = 128):
        self.dim = dim
        self._vectors: Dict[str, EmbeddingVector] = {}

    def _hash_vector(self, text: str) -> List[float]:
        """Deterministic hash-based embedding."""
        seed = hash(text) % (2**31)
        rng = random.Random(seed)
        vec = [rng.uniform(-1, 1) for _ in range(self.dim)]
        # Normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed(self, text: str, vec_id: Optional[str] = None) -> EmbeddingVector:
        eid = vec_id or f"emb-{len(self._vectors)}"
        vec = self._hash_vector(text)
        ev = EmbeddingVector(eid, text, vec)
        self._vectors[eid] = ev
        return ev

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        return dot

    def similarity(self, id_a: str, id_b: str) -> float:
        a = self._vectors.get(id_a)
        b = self._vectors.get(id_b)
        if not a or not b:
            return 0.0
        return self.cosine_similarity(a.vector, b.vector)

    def nearest_neighbors(self, query_id: str, k: int = 5) -> List[Neighbor]:
        query = self._vectors.get(query_id)
        if not query:
            return []
        scored = []
        for ev in self._vectors.values():
            if ev.id == query_id:
                continue
            dist = 1 - self.cosine_similarity(query.vector, ev.vector)  # convert to distance
            scored.append((dist, ev))
        scored.sort()
        return [Neighbor(ev.id, dist, ev.text) for dist, ev in scored[:k]]

    def search(self, query_text: str, k: int = 5) -> List[Neighbor]:
        q_vec = self._hash_vector(query_text)
        scored = []
        for ev in self._vectors.values():
            sim = self.cosine_similarity(q_vec, ev.vector)
            scored.append((1 - sim, ev))
        scored.sort()
        return [Neighbor(ev.id, dist, ev.text) for dist, ev in scored[:k]]

    def cluster(self, k: int = 3, max_iter: int = 10) -> Dict[int, List[str]]:
        """Simple k-means clustering on embeddings."""
        vectors = list(self._vectors.values())
        if len(vectors) < k:
            return {i: [v.id] for i, v in enumerate(vectors)}
        # Random centroids
        rng = random.Random(42)
        centroids = [vectors[i].vector[:] for i in rng.sample(range(len(vectors)), k)]
        for _ in range(max_iter):
            clusters: Dict[int, List[EmbeddingVector]] = defaultdict(list)
            for v in vectors:
                distances = [1 - self.cosine_similarity(v.vector, c) for c in centroids]
                closest = distances.index(min(distances))
                clusters[closest].append(v)
            # Update centroids
            new_centroids = []
            for i in range(k):
                members = clusters.get(i, [])
                if members:
                    new_c = [sum(m.vector[j] for m in members) / len(members) for j in range(self.dim)]
                    norm = math.sqrt(sum(v * v for v in new_c)) or 1.0
                    new_c = [v / norm for v in new_c]
                    new_centroids.append(new_c)
                else:
                    new_centroids.append(centroids[i])
            centroids = new_centroids
        return {i: [v.id for v in members] for i, members in clusters.items()}

    def get_vector(self, vec_id: str) -> Optional[EmbeddingVector]:
        return self._vectors.get(vec_id)

    def get_stats(self) -> Dict[str, Any]:
        return {"vectors": len(self._vectors), "dimension": self.dim}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Embedding Engine")
    print("ai/llm_embedding_engine_native.py")
    print("=" * 60)

    engine = EmbeddingEngine(dim=64)

    # 1. Embed texts
    print("\n[1] Embed Texts")
    texts = [
        "Python programming language",
        "JavaScript web development",
        "Python machine learning",
        "JavaScript frontend framework",
        "Data science with Python",
        "React UI components",
    ]
    for t in texts:
        engine.embed(t)
    print(f"  Embedded {len(texts)} texts")

    # 2. Similarity
    print("\n[2] Cosine Similarity")
    vids = list(engine._vectors.keys())
    for i in range(min(3, len(vids) - 1)):
        sim = engine.similarity(vids[i], vids[i+1])
        print(f"  {vids[i]} vs {vids[i+1]}: {sim:.4f}")

    # 3. Nearest neighbors
    print("\n[3] Nearest Neighbors")
    nn = engine.nearest_neighbors(vids[0], k=3)
    for n in nn:
        print(f"  {n.id} (dist={n.distance:.4f}): {n.text[:40]}...")

    # 4. Search
    print("\n[4] Semantic Search")
    results = engine.search("Python AI", k=3)
    for r in results:
        print(f"  {r.id} (dist={r.distance:.4f}): {r.text[:40]}...")

    # 5. Clustering
    print("\n[5] K-Means Clustering")
    clusters = engine.cluster(k=2)
    for cid, members in clusters.items():
        print(f"  Cluster {cid}: {members}")

    # 6. Stats
    print("\n[6] Engine Stats")
    print(f"  {engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
