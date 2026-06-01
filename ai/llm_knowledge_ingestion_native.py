"""Knowledge Ingestion Pipeline — Document chunking, embedding, and indexing.

Modul ini menyediakan:
- DocumentLoader untuk parsing text, markdown, JSON, CSV
- ChunkingEngine dengan strategies (fixed, semantic, recursive)
- EmbeddingPipeline untuk generating vector representations
- IndexManager untuk inverted index dan vector store simulation
- IngestionOrchestrator untuk end-to-end document ingestion
"""

from __future__ import annotations

import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ChunkStrategy(Enum):
    FIXED_SIZE = auto()
    SEMANTIC = auto()
    RECURSIVE = auto()
    PARAGRAPH = auto()


class DocumentFormat(Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    CSV = "csv"
    HTML = "html"


@dataclass
class DocumentChunk:
    """Single chunk of a document."""
    chunk_id: str
    doc_id: str
    text: str
    start_pos: int
    end_pos: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def token_count(self) -> int:
        return len(self.text.split())


@dataclass
class Document:
    """Full document record."""
    doc_id: str
    title: str
    content: str
    format: DocumentFormat
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    chunks: List[DocumentChunk] = field(default_factory=list)


class DocumentLoader:
    """Load and parse documents from various formats."""

    def load(self, content: str, format: DocumentFormat = DocumentFormat.TEXT,
             title: str = "", source: str = "") -> Document:
        doc_id = str(uuid.uuid4())[:12]
        parsed = self._parse(content, format)
        return Document(
            doc_id=doc_id,
            title=title or f"doc-{doc_id}",
            content=parsed,
            format=format,
            source=source
        )

    def _parse(self, content: str, format: DocumentFormat) -> str:
        if format == DocumentFormat.TEXT:
            return content
        elif format == DocumentFormat.MARKDOWN:
            # Simple markdown stripping (headers, bullets)
            lines = content.split("\n")
            cleaned = []
            for line in lines:
                line = line.lstrip("# ").lstrip("- ").lstrip("* ")
                cleaned.append(line)
            return "\n".join(cleaned)
        elif format == DocumentFormat.JSON:
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    return "\n".join(f"{k}: {v}" for k, v in data.items() if isinstance(v, str))
                elif isinstance(data, list):
                    return "\n".join(str(item) for item in data)
                return str(data)
            except Exception:
                return content
        elif format == DocumentFormat.CSV:
            lines = content.strip().split("\n")
            if len(lines) > 1:
                headers = lines[0].split(",")
                result = []
                for line in lines[1:]:
                    values = line.split(",")
                    row = ", ".join(f"{h}: {v}" for h, v in zip(headers, values))
                    result.append(row)
                return "\n".join(result)
            return content
        elif format == DocumentFormat.HTML:
            # Very simple HTML tag stripping
            import re
            text = re.sub(r'<[^>]+>', ' ', content)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        return content

    def load_batch(self, items: List[Tuple[str, DocumentFormat, str, str]]) -> List[Document]:
        return [self.load(content, fmt, title, source) for content, fmt, title, source in items]


class ChunkingEngine:
    """Chunk documents into smaller pieces."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self._strategies: Dict[ChunkStrategy, Callable[[str, str], List[DocumentChunk]]] = {
            ChunkStrategy.FIXED_SIZE: self._chunk_fixed,
            ChunkStrategy.PARAGRAPH: self._chunk_paragraph,
            ChunkStrategy.RECURSIVE: self._chunk_recursive,
        }

    def chunk(self, doc: Document, strategy: ChunkStrategy = ChunkStrategy.FIXED_SIZE) -> List[DocumentChunk]:
        if strategy in self._strategies:
            chunks = self._strategies[strategy](doc.content, doc.doc_id)
        else:
            chunks = self._chunk_fixed(doc.content, doc.doc_id)
        doc.chunks = chunks
        return chunks

    def _chunk_fixed(self, text: str, doc_id: str) -> List[DocumentChunk]:
        chunks = []
        words = text.split()
        start = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append(DocumentChunk(
                chunk_id=str(uuid.uuid4())[:8],
                doc_id=doc_id,
                text=chunk_text,
                start_pos=start,
                end_pos=end
            ))
            start = end - self.overlap if end < len(words) else end
        return chunks

    def _chunk_paragraph(self, text: str, doc_id: str) -> List[DocumentChunk]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        for i, para in enumerate(paragraphs):
            chunks.append(DocumentChunk(
                chunk_id=str(uuid.uuid4())[:8],
                doc_id=doc_id,
                text=para,
                start_pos=i,
                end_pos=i + 1
            ))
        return chunks

    def _chunk_recursive(self, text: str, doc_id: str) -> List[DocumentChunk]:
        # First split by paragraphs, then by sentences if too long
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        for para in paragraphs:
            if len(para.split()) > self.chunk_size:
                sentences = [s.strip() for s in para.split(". ") if s.strip()]
                current = []
                current_len = 0
                for sent in sentences:
                    sent_len = len(sent.split())
                    if current_len + sent_len > self.chunk_size and current:
                        chunk_text = ". ".join(current) + "."
                        chunks.append(DocumentChunk(
                            chunk_id=str(uuid.uuid4())[:8],
                            doc_id=doc_id,
                            text=chunk_text,
                            start_pos=0,
                            end_pos=0
                        ))
                        current = [sent]
                        current_len = sent_len
                    else:
                        current.append(sent)
                        current_len += sent_len
                if current:
                    chunk_text = ". ".join(current) + "."
                    chunks.append(DocumentChunk(
                        chunk_id=str(uuid.uuid4())[:8],
                        doc_id=doc_id,
                        text=chunk_text,
                        start_pos=0,
                        end_pos=0
                    ))
            else:
                chunks.append(DocumentChunk(
                    chunk_id=str(uuid.uuid4())[:8],
                    doc_id=doc_id,
                    text=para,
                    start_pos=0,
                    end_pos=0
                ))
        return chunks


class EmbeddingPipeline:
    """Simulated embedding generation for chunks."""

    def __init__(self, dim: int = 128):
        self.dim = dim
        self._embeddings: Dict[str, List[float]] = {}

    def embed(self, text: str) -> List[float]:
        if text in self._embeddings:
            return self._embeddings[text]
        h = hashlib.sha256(text.encode()).hexdigest()
        vec = [((int(h[i:i+4], 16) % 1000) / 1000.0 - 0.5) * 2 for i in range(0, 64, 4)]
        vec = (vec * ((self.dim // len(vec)) + 1))[:self.dim]
        self._embeddings[text] = vec
        return vec

    def embed_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        for chunk in chunks:
            chunk.embedding = self.embed(chunk.text)
        return chunks

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if len(a) != len(b) or len(a) == 0:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query: str, chunks: List[DocumentChunk], top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        query_emb = self.embed(query)
        scored = []
        for chunk in chunks:
            if chunk.embedding is None:
                chunk.embedding = self.embed(chunk.text)
            score = self.cosine_similarity(query_emb, chunk.embedding)
            scored.append((chunk, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


class IndexManager:
    """Manage inverted index and vector store."""

    def __init__(self):
        self._inverted_index: Dict[str, Set[str]] = {}  # term -> chunk_ids
        self._chunks: Dict[str, DocumentChunk] = {}
        self._docs: Dict[str, Document] = {}
        self._embedding = EmbeddingPipeline()

    def add_document(self, doc: Document) -> None:
        self._docs[doc.doc_id] = doc
        for chunk in doc.chunks:
            self._chunks[chunk.chunk_id] = chunk
            # Build inverted index
            words = set(chunk.text.lower().split())
            for word in words:
                if len(word) > 2:
                    self._inverted_index.setdefault(word, set()).add(chunk.chunk_id)

    def keyword_search(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, int]]:
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        scores: Dict[str, int] = {}
        for word in query_words:
            for chunk_id in self._inverted_index.get(word, set()):
                scores[chunk_id] = scores.get(chunk_id, 0) + 1
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(self._chunks[cid], score) for cid, score in ranked[:top_k] if cid in self._chunks]

    def semantic_search(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        all_chunks = list(self._chunks.values())
        return self._embedding.search(query, all_chunks, top_k)

    def hybrid_search(self, query: str, top_k: int = 5, alpha: float = 0.5) -> List[Tuple[DocumentChunk, float]]:
        kw_results = self.keyword_search(query, top_k * 2)
        keyword_results = {chunk.chunk_id: score for chunk, score in kw_results}
        semantic_results = self.semantic_search(query, top_k * 2)
        combined: Dict[str, float] = {}
        max_kw = max(keyword_results.values(), default=1)
        for chunk, score in semantic_results:
            kw_score = keyword_results.get(chunk.chunk_id, 0)
            combined[chunk.chunk_id] = alpha * score + (1 - alpha) * (kw_score / max(max_kw, 1))
        ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)
        return [(self._chunks[cid], score) for cid, score in ranked[:top_k] if cid in self._chunks]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "documents": len(self._docs),
            "chunks": len(self._chunks),
            "indexed_terms": len(self._inverted_index),
        }


class IngestionOrchestrator:
    """End-to-end document ingestion pipeline."""

    def __init__(self, chunk_size: int = 500, embedding_dim: int = 128):
        self.loader = DocumentLoader()
        self.chunker = ChunkingEngine(chunk_size=chunk_size)
        self.embedder = EmbeddingPipeline(dim=embedding_dim)
        self.index = IndexManager()
        self._history: List[Dict[str, Any]] = []

    def ingest(self, content: str, format: DocumentFormat = DocumentFormat.TEXT,
               title: str = "", source: str = "", chunk_strategy: ChunkStrategy = ChunkStrategy.FIXED_SIZE) -> Document:
        start = time.time()
        doc = self.loader.load(content, format, title, source)
        chunks = self.chunker.chunk(doc, chunk_strategy)
        self.embedder.embed_chunks(chunks)
        self.index.add_document(doc)
        duration = time.time() - start
        record = {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "chunks": len(chunks),
            "duration": round(duration, 3),
            "format": format.value,
        }
        self._history.append(record)
        return doc

    def search(self, query: str, top_k: int = 5, search_type: str = "hybrid") -> List[Tuple[DocumentChunk, float]]:
        if search_type == "keyword":
            return self.index.keyword_search(query, top_k)
        elif search_type == "semantic":
            return self.index.semantic_search(query, top_k)
        return self.index.hybrid_search(query, top_k)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "history": self._history,
            "index": self.index.get_stats(),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_stats(), f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("KNOWLEDGE INGESTION PIPELINE DEMO")
    print("=" * 70)

    # 1. Document loading
    print("\n[1] Document Loading")
    loader = DocumentLoader()
    docs = loader.load_batch([
        ("Python is a programming language. It is widely used for web development, data science, and AI.", DocumentFormat.TEXT, "Python Overview", "manual"),
        ("# Machine Learning\n\nML is a subset of AI. It uses algorithms to learn from data.\n\n# Deep Learning\n\nDeep learning uses neural networks with many layers.", DocumentFormat.MARKDOWN, "ML Guide", "wiki"),
        ('{"name": "GPT-4", "type": "LLM", "params": "1.8T"}', DocumentFormat.JSON, "GPT-4 Info", "api"),
    ])
    for doc in docs:
        print(f"  {doc.doc_id}: {doc.title} ({doc.format.value}) - {len(doc.content)} chars")

    # 2. Chunking
    print("\n[2] Chunking")
    chunker = ChunkingEngine(chunk_size=20, overlap=5)
    for doc in docs:
        chunks = chunker.chunk(doc, ChunkStrategy.FIXED_SIZE)
        print(f"  {doc.title}: {len(chunks)} chunks")
        for i, c in enumerate(chunks[:3]):
            print(f"    Chunk {i}: {c.text[:60]}...")

    # 3. Embedding
    print("\n[3] Embedding")
    embedder = EmbeddingPipeline(dim=64)
    sample_chunks = docs[0].chunks[:2]
    embedder.embed_chunks(sample_chunks)
    for c in sample_chunks:
        print(f"  {c.chunk_id}: embedding dim={len(c.embedding)}, first 3 values={c.embedding[:3]}")

    # 4. Search
    print("\n[4] Semantic Search")
    all_chunks = []
    for doc in docs:
        all_chunks.extend(doc.chunks)
    embedder.embed_chunks(all_chunks)
    results = embedder.search("artificial intelligence", all_chunks, top_k=3)
    for chunk, score in results:
        print(f"  Score {score:.3f}: {chunk.text[:60]}...")

    # 5. Full ingestion pipeline
    print("\n[5] Full Ingestion Pipeline")
    orchestrator = IngestionOrchestrator(chunk_size=30, embedding_dim=64)
    long_doc = """Artificial Intelligence is transforming industries. 
    Machine learning algorithms process vast amounts of data. 
    Deep learning models achieve human-level performance on many tasks. 
    Natural language processing enables machines to understand text. 
    Computer vision allows systems to interpret images. 
    Robotics combines AI with physical actuators."""
    doc = orchestrator.ingest(long_doc, DocumentFormat.TEXT, "AI Overview", "manual", ChunkStrategy.RECURSIVE)
    print(f"  Ingested: {doc.doc_id} with {len(doc.chunks)} chunks")

    # Search within pipeline
    search_results = orchestrator.search("machine learning", top_k=3)
    print(f"  Search results for 'machine learning':")
    for chunk, score in search_results:
        print(f"    {score:.3f}: {chunk.text[:60]}...")

    # 6. Index stats
    print("\n[6] Index Stats")
    stats = orchestrator.get_stats()
    print(f"  Documents: {stats['index']['documents']}")
    print(f"  Chunks: {stats['index']['chunks']}")
    print(f"  Terms: {stats['index']['indexed_terms']}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
