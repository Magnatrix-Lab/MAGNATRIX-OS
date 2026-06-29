"""
vector_store_connector_native.py
MAGNATRIX-OS — Vector Store Connector

Inspired by Langflow (langflow-ai): Vector store integration for RAG pipelines.
Simulated vector store with in-memory embeddings, similarity search, and CRUD. Pure stdlib.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class VectorDocument:
    doc_id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorStoreConnector:
    """Simulated vector store with in-memory embeddings and similarity search."""

    def __init__(self, store_dir: str = "./vector_store"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(exist_ok=True)
        self.documents: Dict[str, VectorDocument] = {}
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

    def _save(self) -> None:
        with open(self.store_dir / "documents.json", "w", encoding="utf-8") as f:
            json.dump({did: asdict(d) for did, d in self.documents.items()}, f, indent=2)

    def _simple_embed(self, text: str, dim: int = 64) -> List[float]:
        """Generate a simple deterministic embedding from text."""
        import hashlib
        h = hashlib.md5(text.encode()).hexdigest()
        vec = []
        for i in range(dim):
            seed = int(h[i % len(h)], 16) + i * 17
            vec.append((seed % 100) / 100.0)
        return vec

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        return dot / (norm_a * norm_b + 1e-9)

    def add(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> VectorDocument:
        embedding = self._simple_embed(content)
        doc = VectorDocument(doc_id=doc_id, content=content, embedding=embedding, metadata=metadata or {})
        self.documents[doc_id] = doc
        self._save()
        return doc

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_emb = self._simple_embed(query)
        scored = []
        for doc in self.documents.values():
            sim = self._cosine_similarity(query_emb, doc.embedding)
            scored.append((sim, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"doc_id": d.doc_id, "content": d.content[:200], "score": round(s, 4), "metadata": d.metadata} for s, d in scored[:top_k]]

    def delete(self, doc_id: str) -> bool:
        if doc_id in self.documents:
            del self.documents[doc_id]
            self._save()
            return True
        return False

    def get(self, doc_id: str) -> Optional[VectorDocument]:
        return self.documents.get(doc_id)

    def get_stats(self) -> Dict[str, Any]:
        return {"total_documents": len(self.documents)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["VectorStoreConnector", "VectorDocument"]