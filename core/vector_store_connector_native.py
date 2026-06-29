"""
vector_store_connector_native.py
MAGNATRIX-OS — Vector Store Connector

Inspired by langflow-ai/langflow vector store integration:
Connect to and query vector stores for RAG applications. Pure stdlib.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class VectorDocument:
    doc_id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    doc_id: str
    score: float
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorStoreConnector:
    """Connect to and query vector stores for RAG applications."""

    def __init__(self, store_dir: str = "./vector_store"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(exist_ok=True)
        self.documents: Dict[str, VectorDocument] = {}
        self.indices: Dict[str, List[str]] = {}  # index_name -> doc_ids
        self._load()

    def _load(self) -> None:
        file = self.store_dir / "documents.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for did, dd in data.items():
                        self.documents[did] = VectorDocument(**dd)
            except Exception:
                pass
        idx_file = self.store_dir / "indices.json"
        if idx_file.exists():
            try:
                with open(idx_file, "r", encoding="utf-8") as f:
                    self.indices = json.load(f)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.store_dir / "documents.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.documents.items()}, f, indent=2)
        with open(self.store_dir / "indices.json", "w", encoding="utf-8") as f:
            json.dump(self.indices, f, indent=2)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _simple_embed(self, text: str, dim: int = 128) -> List[float]:
        """Simple deterministic embedding for simulation."""
        import hashlib
        h = hashlib.md5(text.encode()).hexdigest()
        vec = []
        for i in range(dim):
            val = int(h[i % len(h)], 16) / 16.0
            if i % 2 == 0:
                val = -val
            vec.append(val)
        return vec

    def add_document(self, index_name: str, doc_id: str, content: str,
                     metadata: Optional[Dict[str, Any]] = None,
                     embedding: Optional[List[float]] = None) -> VectorDocument:
        if embedding is None:
            embedding = self._simple_embed(content)
        doc = VectorDocument(
            doc_id=doc_id, content=content, embedding=embedding,
            metadata=metadata or {},
        )
        self.documents[doc_id] = doc
        if index_name not in self.indices:
            self.indices[index_name] = []
        if doc_id not in self.indices[index_name]:
            self.indices[index_name].append(doc_id)
        self._save()
        return doc

    def search(self, index_name: str, query: str, top_k: int = 5) -> List[SearchResult]:
        if index_name not in self.indices:
            return []
        query_emb = self._simple_embed(query)
        results = []
        for doc_id in self.indices[index_name]:
            doc = self.documents.get(doc_id)
            if doc:
                score = self._cosine_similarity(query_emb, doc.embedding)
                results.append(SearchResult(
                    doc_id=doc_id, score=round(score, 4), content=doc.content, metadata=doc.metadata,
                ))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def delete_document(self, index_name: str, doc_id: str) -> bool:
        if index_name in self.indices and doc_id in self.indices[index_name]:
            self.indices[index_name].remove(doc_id)
            if doc_id in self.documents:
                del self.documents[doc_id]
            self._save()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {"total_documents": len(self.documents), "indices": len(self.indices)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["VectorStoreConnector", "VectorDocument", "SearchResult"]