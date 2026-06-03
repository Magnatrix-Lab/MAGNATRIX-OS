"""LLM Embedding Indexer — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional

@dataclass
class EmbeddingDocument:
    id: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)

class EmbeddingIndexer:
    def __init__(self, dimension: int = 8) -> None:
        self.dimension = dimension
        self._docs: List[EmbeddingDocument] = []
        self._index: Dict[str, int] = {}

    def add(self, doc: EmbeddingDocument) -> None:
        if len(doc.vector) != self.dimension:
            raise ValueError("Vector dimension mismatch")
        if doc.id in self._index:
            self._docs[self._index[doc.id]] = doc
        else:
            self._index[doc.id] = len(self._docs)
            self._docs.append(doc)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        if len(query) != self.dimension:
            raise ValueError("Query dimension mismatch")
        scored = [(doc.id, self._cosine_similarity(query, doc.vector)) for doc in self._docs]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        return {"total": len(self._docs), "dimension": self.dimension}

def run() -> None:
    print("Embedding Indexer test")
    e = EmbeddingIndexer(dimension=8)
    e.add(EmbeddingDocument("doc1", [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
    e.add(EmbeddingDocument("doc2", [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
    e.add(EmbeddingDocument("doc3", [0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
    query = [0.5] * 8
    results = e.search(query, top_k=3)
    print("  Query: " + str(query))
    for doc_id, score in results:
        print("  " + doc_id + ": " + str(score))
    print("  Stats: " + str(e.get_stats()))
    print("Embedding Indexer test complete.")

if __name__ == "__main__":
    run()
