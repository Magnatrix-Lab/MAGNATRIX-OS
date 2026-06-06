#!/usr/bin/env python3
"""
Knowledge Base for MAGNATRIX-OS
Document ingestion, chunking, indexing, and native vector search
for Retrieval-Augmented Generation (RAG). Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    content: str
    position: int
    token_count: int
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "position": self.position,
            "token_count": self.token_count,
        }


@dataclasses.dataclass
class KnowledgeDocument:
    doc_id: str
    title: str
    source: str
    content: str
    chunks: List[DocumentChunk] = dataclasses.field(default_factory=list)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    created_at: float = dataclasses.field(default_factory=time.time)
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "source": self.source,
            "chunks": len(self.chunks),
            "metadata": self.metadata,
        }


class KnowledgeBase:
    """Document ingestion, chunking, and indexing for RAG."""

    def __init__(self, storage_dir: str = "/tmp/magnatrix_kb", chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._documents: Dict[str, KnowledgeDocument] = {}
        self._index_path = self.storage_dir / "kb_index.json"
        self._load()

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def _chunk_text(self, text: str, doc_id: str) -> List[DocumentChunk]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = []
        current_len = 0
        pos = 0
        for sent in sentences:
            sent_len = len(sent)
            if current_len + sent_len > self.chunk_size and current:
                content = " ".join(current)
                chunk_id = hashlib.sha256((doc_id + content + str(pos)).encode()).hexdigest()[:16]
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id, doc_id=doc_id, content=content,
                    position=pos, token_count=self._estimate_tokens(content)
                ))
                pos += 1
                # Overlap
                overlap = []
                overlap_len = 0
                for s in reversed(current):
                    if overlap_len + len(s) > self.chunk_overlap:
                        break
                    overlap.insert(0, s)
                    overlap_len += len(s)
                current = overlap + [sent]
                current_len = overlap_len + sent_len
            else:
                current.append(sent)
                current_len += sent_len
        if current:
            content = " ".join(current)
            chunk_id = hashlib.sha256((doc_id + content + str(pos)).encode()).hexdigest()[:16]
            chunks.append(DocumentChunk(
                chunk_id=chunk_id, doc_id=doc_id, content=content,
                position=pos, token_count=self._estimate_tokens(content)
            ))
        return chunks

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest(self, doc_id: str, title: str, content: str, source: str = "user", metadata: Optional[Dict[str, Any]] = None) -> KnowledgeDocument:
        checksum = hashlib.sha256(content.encode()).hexdigest()
        # Check for duplicate
        existing = self._documents.get(doc_id)
        if existing and existing.checksum == checksum:
            return existing
        chunks = self._chunk_text(content, doc_id)
        doc = KnowledgeDocument(
            doc_id=doc_id, title=title, source=source, content=content,
            chunks=chunks, metadata=metadata or {}, checksum=checksum,
        )
        self._documents[doc_id] = doc
        self._save()
        return doc

    def ingest_file(self, file_path: str, doc_id: Optional[str] = None, title: Optional[str] = None) -> KnowledgeDocument:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="replace")
        doc_id = doc_id or path.stem
        title = title or path.name
        return self.ingest(doc_id, title, content, source=str(path))

    def delete(self, doc_id: str) -> bool:
        if doc_id in self._documents:
            del self._documents[doc_id]
            self._save()
            return True
        return False

    def get(self, doc_id: str) -> Optional[KnowledgeDocument]:
        return self._documents.get(doc_id)

    def list_all(self) -> List[KnowledgeDocument]:
        return list(self._documents.values())

    # ------------------------------------------------------------------
    # Search (TF-IDF + cosine similarity via token overlap)
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> Set[str]:
        return set(re.findall(r'\b\w+\b', text.lower()))

    def _tfidf_vector(self, text: str, corpus: List[str]) -> Dict[str, float]:
        tokens = self._tokenize(text)
        N = len(corpus) + 1
        vector = {}
        for token in tokens:
            tf = 1 + text.lower().count(token)
            df = sum(1 for doc in corpus if token in doc.lower()) + 1
            idf = math.log(N / df)
            vector[token] = tf * idf
        return vector

    def _cosine_similarity(self, v1: Dict[str, float], v2: Dict[str, float]) -> float:
        all_keys = set(v1.keys()) | set(v2.keys())
        dot = sum(v1.get(k, 0) * v2.get(k, 0) for k in all_keys)
        norm1 = math.sqrt(sum(v ** 2 for v in v1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in v2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        if not self._documents:
            return []
        corpus = [doc.content for doc in self._documents.values()]
        query_vec = self._tfidf_vector(query, corpus)
        scored = []
        for doc in self._documents.values():
            for chunk in doc.chunks:
                chunk_vec = self._tfidf_vector(chunk.content, corpus)
                score = self._cosine_similarity(query_vec, chunk_vec)
                if score > 0.05:
                    scored.append((chunk, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def search_documents(self, query: str, top_k: int = 5) -> List[Tuple[KnowledgeDocument, float]]:
        doc_scores = {}
        for chunk, score in self.search(query, top_k * 3):
            doc_scores[chunk.doc_id] = max(doc_scores.get(chunk.doc_id, 0), score)
        docs = [(self._documents[did], score) for did, score in doc_scores.items() if did in self._documents]
        docs.sort(key=lambda x: x[1], reverse=True)
        return docs[:top_k]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        data = []
        for doc in self._documents.values():
            data.append({
                "doc_id": doc.doc_id,
                "title": doc.title,
                "source": doc.source,
                "content": doc.content,
                "chunks": [dataclasses.asdict(c) for c in doc.chunks],
                "metadata": doc.metadata,
                "created_at": doc.created_at,
                "checksum": doc.checksum,
            })
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        if not self._index_path.exists():
            return
        try:
            with open(self._index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                doc = KnowledgeDocument(
                    doc_id=item["doc_id"], title=item["title"], source=item["source"],
                    content=item["content"], metadata=item.get("metadata", {}),
                    created_at=item.get("created_at", time.time()),
                    checksum=item.get("checksum", ""),
                )
                doc.chunks = [DocumentChunk(
                    chunk_id=c["chunk_id"], doc_id=c["doc_id"], content=c["content"],
                    position=c["position"], token_count=c["token_count"],
                ) for c in item.get("chunks", [])]
                self._documents[doc.doc_id] = doc
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        total_chunks = sum(len(d.chunks) for d in self._documents.values())
        total_tokens = sum(c.token_count for d in self._documents.values() for c in d.chunks)
        return {
            "documents": len(self._documents),
            "chunks": total_chunks,
            "estimated_tokens": total_tokens,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "storage_dir": str(self.storage_dir),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile, shutil
    tmp = tempfile.mkdtemp(prefix="magnatrix_kb_")
    kb = KnowledgeBase(tmp, chunk_size=200, chunk_overlap=30)
    print("=== Knowledge Base Demo ===\n")
    # Ingest documents
    kb.ingest("py_guide", "Python Guide", "Python is a programming language. It supports object-oriented programming. Python has many libraries. You can use Python for web development. Python is easy to learn.", source="manual")
    kb.ingest("js_guide", "JavaScript Guide", "JavaScript is a web language. It runs in browsers. JavaScript supports async programming. You can build full-stack apps with JavaScript.", source="manual")
    # Stats
    print(f"Stats: {kb.stats()}")
    # Search
    print(f"\nSearch 'python':")
    for chunk, score in kb.search("python programming", top_k=3):
        print(f"  [{score:.3f}] {chunk.content[:80]}...")
    # Document search
    print(f"\nDocument search 'web':")
    for doc, score in kb.search_documents("web development", top_k=2):
        print(f"  [{score:.3f}] {doc.title}")
    # Cleanup
    shutil.rmtree(tmp)
    print("\nCleanup complete.")


if __name__ == "__main__":
    _demo()
