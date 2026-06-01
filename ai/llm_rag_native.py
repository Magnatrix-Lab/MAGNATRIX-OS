#!/usr/bin/env python3
"""
ai/llm_rag_native.py
MAGNATRIX-OS — Vector RAG Engine for the LLM Arena
AMATI pattern: retrieval-augmented generation with chunking, embeddings, reranking

Pure Python, stdlib only. Simulates document chunking, dense vector storage,
similarity search, and context assembly.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _token_count(text: str) -> int:
    return len(text) // 4 + 1


def _cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _hash_vector(text: str, dim: int = 128) -> List[float]:
    """Deterministic pseudo-vector from text."""
    seed = sum(ord(c) * 31 ** i for i, c in enumerate(text[:64]))
    random_state = seed % 100000
    vec = []
    for i in range(dim):
        random_state = (random_state * 1103515245 + 12345) & 0x7FFFFFFF
        val = (random_state / 0x7FFFFFFF) * 2 - 1
        vec.append(val)
    return vec


# ───────────────────────────────────────────────────────────────
# 1. DOCUMENT CHUNKER
# ───────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentChunker:
    """Split documents into chunks with configurable overlap."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        chunks = []
        step = self.chunk_size - self.overlap
        pos = 0
        idx = 0
        while pos < len(text):
            end = min(pos + self.chunk_size, len(text))
            chunk_text = text[pos:end]
            chunks.append(Chunk(
                chunk_id=f"{doc_id}_c{idx}",
                doc_id=doc_id,
                text=chunk_text,
                start_pos=pos,
                end_pos=end,
                metadata=metadata or {},
            ))
            pos += step
            idx += 1
            if end == len(text):
                break
        return chunks


# ───────────────────────────────────────────────────────────────
# 2. VECTOR STORE
# ───────────────────────────────────────────────────────────────

@dataclass
class VectorEntry:
    chunk_id: str
    vector: List[float]
    text: str
    metadata: Dict[str, Any]


class VectorStore:
    """Simulated dense vector storage with cosine similarity search."""

    def __init__(self, dim: int = 128) -> None:
        self.dim = dim
        self._entries: List[VectorEntry] = []

    def add(self, chunk: Chunk) -> None:
        vec = _hash_vector(chunk.text, self.dim)
        self._entries.append(VectorEntry(
            chunk_id=chunk.chunk_id,
            vector=vec,
            text=chunk.text,
            metadata=chunk.metadata,
        ))

    def add_batch(self, chunks: List[Chunk]) -> None:
        for c in chunks:
            self.add(c)

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[VectorEntry, float]]:
        scored = []
        for e in self._entries:
            sim = _cosine_sim(query_vector, e.vector)
            scored.append((e, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def stats(self) -> Dict[str, Any]:
        return {"entries": len(self._entries), "dim": self.dim}


# ───────────────────────────────────────────────────────────────
# 3. QUERY ENCODER
# ───────────────────────────────────────────────────────────────

class QueryEncoder:
    """Encode queries into vectors for similarity search."""

    def __init__(self, dim: int = 128) -> None:
        self.dim = dim

    def encode(self, query: str) -> List[float]:
        return _hash_vector(query, self.dim)


# ───────────────────────────────────────────────────────────────
# 4. RERANKER
# ───────────────────────────────────────────────────────────────

class Reranker:
    """Re-rank retrieved chunks by relevance, recency, and diversity."""

    def rerank(self, results: List[Tuple[VectorEntry, float]], query: str, top_k: int = 5) -> List[Tuple[VectorEntry, float]]:
        scored = []
        for e, sim in results:
            # Relevance score (base similarity)
            relevance = sim
            # Recency boost (if metadata has timestamp)
            recency = 0.0
            if "timestamp" in e.metadata:
                age = _now() - e.metadata["timestamp"]
                recency = max(0, 1.0 - age / 86400) * 0.1
            # Diversity penalty (similarity to already selected)
            diversity_penalty = 0.0
            score = relevance + recency - diversity_penalty
            scored.append((e, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        # Remove duplicates by chunk_id
        seen = set()
        unique = []
        for e, score in scored:
            if e.chunk_id not in seen:
                seen.add(e.chunk_id)
                unique.append((e, score))
        return unique[:top_k]


# ───────────────────────────────────────────────────────────────
# 5. CONTEXT ASSEMBLER
# ───────────────────────────────────────────────────────────────

class ContextAssembler:
    """Assemble retrieved chunks into a coherent context window."""

    def __init__(self, max_tokens: int = 1024) -> None:
        self.max_tokens = max_tokens

    def assemble(self, chunks: List[Tuple[VectorEntry, float]], query: str = "") -> str:
        parts = []
        if query:
            parts.append(f"[QUERY] {query}")
        total_tokens = _token_count(query) if query else 0
        for e, score in chunks:
            chunk_tokens = _token_count(e.text)
            if total_tokens + chunk_tokens > self.max_tokens:
                break
            parts.append(f"[CHUNK {e.chunk_id} | score={score:.3f}]\n{e.text}")
            total_tokens += chunk_tokens
        return "\n\n".join(parts)

    def assemble_json(self, chunks: List[Tuple[VectorEntry, float]], query: str = "") -> Dict[str, Any]:
        return {
            "query": query,
            "chunks_used": len(chunks),
            "total_tokens": _token_count(self.assemble(chunks, query)),
            "context": self.assemble(chunks, query),
        }


# ───────────────────────────────────────────────────────────────
# 6. RETRIEVAL PIPELINE
# ───────────────────────────────────────────────────────────────

class RetrievalPipeline:
    """Main orchestrator: chunk -> encode -> search -> rerank -> assemble."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50, dim: int = 128, max_context_tokens: int = 1024) -> None:
        self.chunker = DocumentChunker(chunk_size, overlap)
        self.store = VectorStore(dim)
        self.encoder = QueryEncoder(dim)
        self.reranker = Reranker()
        self.assembler = ContextAssembler(max_context_tokens)

    def ingest(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        chunks = self.chunker.chunk(doc_id, text, metadata)
        self.store.add_batch(chunks)

    def query(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        query_vec = self.encoder.encode(query)
        raw_results = self.store.search(query_vec, top_k=top_k * 2)
        reranked = self.reranker.rerank(raw_results, query, top_k)
        return self.assembler.assemble_json(reranked, query)

    def stats(self) -> Dict[str, Any]:
        return {"store": self.store.stats(), "chunker": {"chunk_size": self.chunker.chunk_size, "overlap": self.chunker.overlap}}


# ───────────────────────────────────────────────────────────────
# 7. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Vector RAG Engine Demo")
    print("=" * 60)

    rag = RetrievalPipeline(chunk_size=300, overlap=30, max_context_tokens=512)

    docs = [
        ("doc_1", "Python is a high-level programming language. It is widely used for web development, data science, and automation. Python's syntax is clean and readable. It supports multiple programming paradigms including object-oriented and functional programming. The Python ecosystem includes libraries like NumPy, Pandas, and Django."),
        ("doc_2", "Machine learning is a subset of artificial intelligence. It involves training models on data to make predictions. Common algorithms include linear regression, decision trees, and neural networks. Deep learning uses multi-layer neural networks to learn complex patterns. Frameworks like TensorFlow and PyTorch are popular."),
        ("doc_3", "Quantum computing uses quantum bits or qubits. Unlike classical bits that are 0 or 1, qubits can exist in superposition. This allows quantum computers to solve certain problems exponentially faster than classical computers. Shor's algorithm can factor large numbers efficiently. Grover's algorithm speeds up database searches."),
    ]

    for doc_id, text in docs:
        rag.ingest(doc_id, text, {"timestamp": _now(), "source": "demo"})

    queries = [
        "What is Python used for?",
        "Tell me about neural networks and deep learning",
        "How do quantum computers work?",
    ]

    for q in queries:
        print(f"\n[QUERY] {q}")
        result = rag.query(q, top_k=3)
        print(f"  Chunks used: {result['chunks_used']}")
        print(f"  Total tokens: {result['total_tokens']}")
        print(f"  Context preview:\n{result['context'][:300]}...")

    print(f"\n[STATS] {json.dumps(rag.stats(), indent=2)}")

    print("\n" + "=" * 60)
    print("Demo complete. RAG Engine ready for LLM Arena.")
    print("=" * 60)
