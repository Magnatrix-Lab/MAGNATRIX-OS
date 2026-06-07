#!/usr/bin/env python3
"""
Document Intelligence Module for MAGNATRIX-OS
Upload, parse, index, and chat with any document — PDF, CSV, TXT, JSON, MD.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class DocumentChunk:
    """A chunk of text from a document with metadata."""
    text: str
    doc_id: str
    chunk_index: int
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Result from semantic search over documents."""
    chunk: DocumentChunk
    score: float


@dataclass
class IngestionResult:
    """Result of document ingestion."""
    doc_id: str
    source: str
    chunks: int
    chars: int
    success: bool
    error: Optional[str] = None


class DocumentParser:
    """Parse various document formats into plain text."""

    @staticmethod
    def parse_txt(content: bytes) -> str:
        return content.decode("utf-8", errors="ignore")

    @staticmethod
    def parse_csv(content: bytes) -> str:
        text = content.decode("utf-8", errors="ignore")
        lines = text.splitlines()
        if not lines:
            return ""
        reader = csv.reader(lines)
        rows = [" | ".join(row) for row in reader]
        return "\n".join(rows)

    @staticmethod
    def parse_json(content: bytes) -> str:
        try:
            data = json.loads(content.decode("utf-8", errors="ignore"))
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            return content.decode("utf-8", errors="ignore")

    @staticmethod
    def parse_md(content: bytes) -> str:
        text = content.decode("utf-8", errors="ignore")
        # Strip basic markdown syntax
        text = re.sub(r"#{1,6}\s*", "", text)
        text = re.sub(r"\*\*([^\*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^\*]+)\*", r"\1", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # capture link text
        return text

    @staticmethod
    def parse_pdf(content: bytes) -> str:
        """Basic PDF text extraction via pattern matching."""
        # Try to find text streams between stream/endstream
        text = ""
        # Find text objects in PDF
        for match in re.finditer(br"stream\r?\n(.+?)\r?\nendstream", content, re.DOTALL):
            stream = match.group(1)
            # Look for text extraction markers
            if b"BT" in stream[:20] and b"ET" in stream[-20:]:
                # Extract text between Tj and TJ operators
                for tm in re.finditer(rb"\((.+?)\)\s*Tj", stream):
                    try:
                        text += tm.group(1).decode("utf-8", errors="ignore") + " "
                    except Exception:
                        pass
                for tm in re.finditer(rb"\[(.*?)\]\s*TJ", stream):
                    try:
                        tj = tm.group(1)
                        # Extract parenthesized strings from TJ array
                        for pm in re.finditer(rb"\((.+?)\)", tj):
                            text += pm.group(1).decode("utf-8", errors="ignore") + " "
                    except Exception:
                        pass
        if text:
            return text
        # Fallback: try to extract any readable strings
        strings = []
        for match in re.finditer(br"\((?:[^()\\]|\\.)+\)", content):
            try:
                s = match.group(0)[1:-1].decode("utf-8", errors="ignore")
                if len(s) > 3 and any(c.isalpha() for c in s):
                    strings.append(s)
            except Exception:
                pass
        return "\n".join(strings)

    @classmethod
    def parse(cls, content: bytes, filename: str) -> str:
        ext = Path(filename).suffix.lower()
        parsers = {
            ".txt": cls.parse_txt,
            ".csv": cls.parse_csv,
            ".json": cls.parse_json,
            ".md": cls.parse_md,
            ".pdf": cls.parse_pdf,
            ".html": cls.parse_txt,
            ".htm": cls.parse_txt,
            ".py": cls.parse_txt,
            ".js": cls.parse_txt,
            ".yaml": cls.parse_txt,
            ".yml": cls.parse_txt,
        }
        parser = parsers.get(ext, cls.parse_txt)
        return parser(content)


class TextChunker:
    """Chunk text into overlapping segments for RAG."""

    def __init__(self, chunk_size: int = 800, overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, doc_id: str, source: str) -> List[DocumentChunk]:
        chunks = []
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        current = ""
        idx = 0
        for sent in sentences:
            if len(current) + len(sent) < self.chunk_size:
                current += " " + sent if current else sent
            else:
                if current:
                    chunks.append(DocumentChunk(current.strip(), doc_id, idx, source))
                    idx += 1
                current = sent
        if current:
            chunks.append(DocumentChunk(current.strip(), doc_id, idx, source))
        return chunks


class SimpleVectorStore:
    """In-memory vector store using TF-IDF-like keyword vectors.
    Pure stdlib — no numpy/torch needed.
    """

    def __init__(self) -> None:
        self._chunks: List[DocumentChunk] = []
        self._vectors: List[Dict[str, float]] = []
        self._idf: Dict[str, float] = {}
        self._lock = threading.RLock()

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())

    def _vectorize(self, text: str) -> Dict[str, float]:
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        tf: Dict[str, float] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        max_tf = max(tf.values(), default=1)
        # TF-IDF weighting
        vec: Dict[str, float] = {}
        for t, count in tf.items():
            idf = self._idf.get(t, 1.0)
            vec[t] = (count / max_tf) * idf
        return vec

    def _update_idf(self, all_texts: List[str]) -> None:
        doc_freq: Dict[str, int] = {}
        for text in all_texts:
            seen = set(self._tokenize(text))
            for t in seen:
                doc_freq[t] = doc_freq.get(t, 0) + 1
        n = len(all_texts) if all_texts else 1
        self._idf = {t: 1.0 + (n / (df + 1)) for t, df in doc_freq.items()}

    def _cosine_sim(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(a.get(k, 0) * b.get(k, 0) for k in a)
        norm_a = sum(v * v for v in a.values()) ** 0.5
        norm_b = sum(v * v for v in b.values()) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def add(self, chunks: List[DocumentChunk]) -> None:
        with self._lock:
            # Update IDF with new texts
            all_texts = [c.text for c in self._chunks + chunks]
            self._update_idf(all_texts)
            # Re-vectorize existing
            self._vectors = [self._vectorize(c.text) for c in self._chunks + chunks]
            self._chunks = self._chunks + chunks

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        with self._lock:
            if not self._chunks:
                return []
            q_vec = self._vectorize(query)
            results = []
            for chunk, vec in zip(self._chunks, self._vectors):
                score = self._cosine_sim(q_vec, vec)
                if score > 0.01:
                    results.append(SearchResult(chunk, score))
            results.sort(key=lambda r: r.score, reverse=True)
            return results[:top_k]

    def delete_doc(self, doc_id: str) -> int:
        with self._lock:
            removed = [c for c in self._chunks if c.doc_id != doc_id]
            deleted_count = len(self._chunks) - len(removed)
            self._chunks = removed
            all_texts = [c.text for c in self._chunks]
            self._update_idf(all_texts)
            self._vectors = [self._vectorize(c.text) for c in self._chunks]
            return deleted_count

    def list_docs(self) -> List[Dict[str, Any]]:
        with self._lock:
            docs: Dict[str, Dict[str, Any]] = {}
            for c in self._chunks:
                if c.doc_id not in docs:
                    docs[c.doc_id] = {"doc_id": c.doc_id, "source": c.source, "chunks": 0, "chars": 0}
                docs[c.doc_id]["chunks"] += 1
                docs[c.doc_id]["chars"] += len(c.text)
            return sorted(docs.values(), key=lambda d: d["source"])

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "chunks": len(self._chunks),
                "docs": len(self.list_docs()),
                "vocab": len(self._idf),
            }

    def clear(self) -> None:
        with self._lock:
            self._chunks = []
            self._vectors = []
            self._idf = {}


class DocumentIntelligence:
    """Main entry point: ingest documents and query them."""

    def __init__(self, store_dir: Optional[str] = None, chunk_size: int = 800, overlap: int = 100) -> None:
        self.store_dir = Path(store_dir) if store_dir else Path("./doc_store")
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.chunker = TextChunker(chunk_size, overlap)
        self.vector_store = SimpleVectorStore()
        self._uploads: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def ingest(self, filename: str, content: bytes, metadata: Optional[Dict[str, Any]] = None) -> IngestionResult:
        """Ingest a document from raw bytes."""
        try:
            text = DocumentParser.parse(content, filename)
            if not text or not text.strip():
                return IngestionResult(doc_id="", source=filename, chunks=0, chars=0, success=False, error="Empty or unparsable document")
            doc_id = str(uuid.uuid4())[:8]
            chunks = self.chunker.chunk(text, doc_id, filename)
            for c in chunks:
                c.metadata = metadata or {}
                c.metadata["filename"] = filename
            self.vector_store.add(chunks)
            # Save raw to disk
            raw_path = self.store_dir / f"{doc_id}_{filename}"
            raw_path.write_bytes(content)
            with self._lock:
                self._uploads[doc_id] = {
                    "doc_id": doc_id, "filename": filename, "chunks": len(chunks),
                    "chars": len(text), "path": str(raw_path), "metadata": metadata or {},
                    "ingested_at": time.time(),
                }
            return IngestionResult(doc_id=doc_id, source=filename, chunks=len(chunks), chars=len(text), success=True)
        except Exception as e:
            return IngestionResult(doc_id="", source=filename, chunks=0, chars=0, success=False, error=str(e))

    def ingest_file(self, filepath: str, metadata: Optional[Dict[str, Any]] = None) -> IngestionResult:
        """Ingest from filesystem path."""
        path = Path(filepath)
        if not path.exists():
            return IngestionResult(doc_id="", source=filepath, chunks=0, chars=0, success=False, error="File not found")
        return self.ingest(path.name, path.read_bytes(), metadata)

    def query(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """Query the document knowledge base."""
        results = self.vector_store.search(question, top_k)
        if not results:
            return {"answer": "No relevant documents found. Try uploading a document first.", "sources": []}
        # Build context from top results
        context_parts = []
        sources = []
        for i, r in enumerate(results):
            ctx_line = f"[Excerpt {i+1} from {r.chunk.source}]: {r.chunk.text[:300]}..."
            context_parts.append(ctx_line)
            sources.append({
                "source": r.chunk.source,
                "score": round(r.score, 4),
                "chunk_index": r.chunk.chunk_index,
            })
        context = "\n\n".join(context_parts)
        # Build answer prompt (to be sent to LLM)
        answer = f"Based on the uploaded documents, I found the following relevant information:\n\n{context}\n\n(To get a synthesized answer, route this context to the LLM adapter.)"
        return {
            "answer": answer,
            "sources": sources,
            "context": context,
            "chunks_used": len(results),
        }

    def chat(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """Chat interface — alias for query with LLM integration."""
        result = self.query(question, top_k)
        # Try to route to LLM adapter if available
        try:
            import importlib
            llm_mod = importlib.import_module("core.multi_model_llm_adapter_native")
            adapter = llm_mod.MultiModelLLMAdapter()
            if hasattr(adapter, "chat_mock"):
                prompt = f"Answer based on this context:\n{result['context']}\n\nQuestion: {question}"
                mock = adapter.chat_mock(prompt)
                if mock:
                    result["answer"] = mock.text
        except Exception:
            pass
        return result

    def delete(self, doc_id: str) -> bool:
        """Delete a document from the store."""
        removed = self.vector_store.delete_doc(doc_id)
        with self._lock:
            if doc_id in self._uploads:
                path = self._uploads[doc_id].get("path")
                if path and os.path.exists(path):
                    os.remove(path)
                del self._uploads[doc_id]
        return removed > 0

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all ingested documents."""
        return self.vector_store.list_docs()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "vector_store": self.vector_store.stats(),
            "uploads": len(self._uploads),
            "store_dir": str(self.store_dir),
        }

    def save(self) -> str:
        """Persist vector store index to disk."""
        data = {
            "chunks": [
                {
                    "text": c.text, "doc_id": c.doc_id, "chunk_index": c.chunk_index,
                    "source": c.source, "metadata": c.metadata,
                }
                for c in self.vector_store._chunks
            ],
            "uploads": self._uploads,
            "idf": self.vector_store._idf,
        }
        path = self.store_dir / "index.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def load(self) -> bool:
        """Load vector store index from disk."""
        path = self.store_dir / "index.json"
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            chunks = [
                DocumentChunk(c["text"], c["doc_id"], c["chunk_index"], c["source"], c.get("metadata", {}))
                for c in data.get("chunks", [])
            ]
            self.vector_store._chunks = chunks
            self.vector_store._idf = data.get("idf", {})
            self.vector_store._vectors = [self.vector_store._vectorize(c.text) for c in chunks]
            with self._lock:
                self._uploads = data.get("uploads", {})
            return True
        except Exception:
            return False


class UploadHandler:
    """Parse multipart/form-data from raw HTTP body — native stdlib."""

    @staticmethod
    def parse_multipart(body: bytes, boundary: bytes) -> List[Dict[str, Any]]:
        parts = []
        if not boundary:
            return parts
        delimiter = b"--" + boundary
        chunks = body.split(delimiter)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk or chunk == b"--":
                continue
            # Parse headers
            header_end = chunk.find(b"\r\n\r\n")
            if header_end == -1:
                header_end = chunk.find(b"\n\n")
                sep = 2
            else:
                sep = 4
            if header_end == -1:
                continue
            headers = chunk[:header_end].decode("utf-8", errors="ignore")
            data = chunk[header_end + sep:]
            # Remove trailing \r\n
            if data.endswith(b"\r\n"):
                data = data[:-2]
            # Find filename
            filename = None
            name = None
            for line in headers.splitlines():
                if line.lower().startswith("content-disposition"):
                    for part in line.split(";"):
                        part = part.strip()
                        if part.startswith("filename="):
                            filename = part[10:-1].strip('"')
                        elif part.startswith("name="):
                            name = part[6:-1].strip('"')
            parts.append({"name": name, "filename": filename, "data": data, "headers": headers})
        return parts

    @classmethod
    def extract_files(cls, body: bytes, content_type: str) -> List[Dict[str, Any]]:
        if "multipart/form-data" not in content_type:
            return []
        # Extract boundary
        boundary = None
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary = part[9:].strip('"').encode()
        if not boundary:
            return []
        return cls.parse_multipart(body, boundary)


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Document Intelligence Demo ===\n")
    di = DocumentIntelligence(store_dir="/tmp/doc_test")

    # Ingest sample documents
    docs = [
        ("ai_report.txt", b"Artificial intelligence is transforming industries. Machine learning models can process vast amounts of data. Deep learning uses neural networks with many layers. AGI remains the ultimate goal of AI research."),
        ("data.csv", b"name,age,role\nAlice,30,Engineer\nBob,25,Designer\nCharlie,35,Manager"),
        ("notes.md", b"# Project Notes\n\n## Goals\n- Build autonomous AI\n- Create self-learning system\n\n## Timeline\nQ1: Research\nQ2: Prototype"),
    ]

    for filename, content in docs:
        result = di.ingest(filename, content)
        print(f"Ingested {filename}: {result.chunks} chunks, {result.chars} chars, success={result.success}")

    print(f"\nStore stats: {di.get_stats()}")
    print(f"\nDocuments: {di.list_documents()}")

    print("\n--- Query: 'neural networks' ---")
    q = di.query("neural networks")
    print(f"Sources: {len(q['sources'])}")
    for s in q['sources']:
        print(f"  - {s['source']} (score: {s['score']})")

    print("\n--- Query: 'who is the manager' ---")
    q = di.query("who is the manager")
    print(f"Sources: {len(q['sources'])}")
    for s in q['sources']:
        print(f"  - {s['source']} (score: {s['score']})")

    # Save and reload
    path = di.save()
    print(f"\nSaved index to {path}")
    di2 = DocumentIntelligence(store_dir="/tmp/doc_test")
    ok = di2.load()
    print(f"Loaded index: {ok}")
    print(f"Loaded stats: {di2.get_stats()}")


if __name__ == "__main__":
    _demo()
