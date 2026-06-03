#!/usr/bin/env python3
"""
MAGNATRIX-OS — Semantic Search Engine
ai/llm_semantic_search_native.py

Features:
- Document indexing with semantic vectors
- Query vector generation (simulation)
- Cosine similarity ranking
- Query expansion (synonym injection)
- Faceted filtering (by category, date, author)

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
logger = logging.getLogger("semantic_search")


@dataclass
class SearchDocument:
    id: str
    title: str
    content: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticSearchEngine:
    """Semantic search with vector similarity and faceted filtering."""

    def __init__(self, dim: int = 128):
        self.dim = dim
        self._docs: Dict[str, SearchDocument] = {}
        self._synonyms: Dict[str, List[str]] = {
            "python": ["programming", "coding", "scripting"],
            "ai": ["artificial intelligence", "machine learning", "deep learning"],
            "web": ["internet", "online", "browser"],
            "cloud": ["aws", "azure", "gcp", "hosting"],
        }

    def _text_to_vector(self, text: str) -> List[float]:
        seed = hash(text) % (2**31)
        rng = random.Random(seed)
        vec = [rng.uniform(-1, 1) for _ in range(self.dim)]
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def index(self, doc: SearchDocument) -> None:
        if not doc.vector:
            doc.vector = self._text_to_vector(doc.content)
        self._docs[doc.id] = doc

    def _expand_query(self, query: str) -> str:
        words = query.lower().split()
        expanded = set(words)
        for w in words:
            if w in self._synonyms:
                expanded.update(self._synonyms[w])
        return " ".join(expanded)

    def search(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Tuple[SearchDocument, float]]:
        expanded = self._expand_query(query)
        q_vec = self._text_to_vector(expanded)
        scored = []
        for doc in self._docs.values():
            if filters:
                match = all(doc.metadata.get(k) == v for k, v in filters.items())
                if not match:
                    continue
            sim = self._cosine(q_vec, doc.vector)
            scored.append((doc, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _cosine(self, a: List[float], b: List[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    def get_stats(self) -> Dict[str, Any]:
        return {"documents": len(self._docs), "dimension": self.dim}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Semantic Search Engine")
    print("ai/llm_semantic_search_native.py")
    print("=" * 60)

    engine = SemanticSearchEngine(dim=64)

    docs = [
        SearchDocument("d1", "Python Tutorial", "Learn Python programming language basics", [], {"category": "tech", "author": "Alice"}),
        SearchDocument("d2", "AI Overview", "Introduction to artificial intelligence and machine learning", [], {"category": "tech", "author": "Bob"}),
        SearchDocument("d3", "Web Dev", "Building web applications with JavaScript and cloud hosting", [], {"category": "tech", "author": "Carol"}),
        SearchDocument("d4", "Cloud Guide", "AWS Azure and GCP comparison for cloud infrastructure", [], {"category": "tech", "author": "Alice"}),
        SearchDocument("d5", "Cooking", "Italian pasta recipes and cooking techniques", [], {"category": "food", "author": "Dave"}),
    ]
    for doc in docs:
        engine.index(doc)

    # Search
    for query in ["python coding", "ai ml", "cloud hosting", "pasta"]:
        results = engine.search(query, top_k=3)
        print(f"\nQuery: '{query}'")
        for doc, score in results:
            print(f"  {doc.title} (score={score:.4f})")

    # Filtered search
    print("\n[Filtered] Author=Alice:")
    results = engine.search("tech", top_k=3, filters={"author": "Alice"})
    for doc, score in results:
        print(f"  {doc.title} (score={score:.4f})")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
