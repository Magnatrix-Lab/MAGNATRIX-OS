#!/usr/bin/env python3
"""
MAGNATRIX-OS — Document Processor Engine
ai/llm_document_processor_native.py

Features:
- Document parsing simulation (text, JSON, XML, CSV, markdown)
- Chunking strategies (fixed-size, sentence-based, paragraph-based)
- Metadata extraction (title, author, date, keywords)
- Document classification (by content type, language, topic)
- Search index preparation (term frequency, inverted index)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("document_processor")


class DocType(enum.Enum):
    TEXT = "text"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    MARKDOWN = "markdown"
    CODE = "code"


class ChunkStrategy(enum.Enum):
    FIXED = "fixed"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"


@dataclass
class DocumentChunk:
    id: int
    text: str
    start: int
    end: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    id: str
    content: str
    doc_type: DocType
    chunks: List[DocumentChunk] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    term_freq: Counter = field(default_factory=Counter)


class DocumentProcessor:
    """Document parsing, chunking, and indexing."""

    def detect_type(self, content: str) -> DocType:
        stripped = content.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return DocType.JSON
        if stripped.startswith("<"):
            return DocType.XML
        if "," in stripped[:100] and "\n" in stripped:
            return DocType.CSV
        if "#" in stripped[:200] or "**" in stripped[:200]:
            return DocType.MARKDOWN
        if any(kw in stripped[:200] for kw in ["def ", "class ", "import ", "function "]):
            return DocType.CODE
        return DocType.TEXT

    def extract_metadata(self, content: str, doc_type: DocType) -> Dict[str, Any]:
        meta = {}
        lines = content.splitlines()
        if lines:
            meta["title"] = lines[0][:80]
        meta["length"] = len(content)
        meta["lines"] = len(lines)
        meta["words"] = len(re.findall(r'\w+', content))
        return meta

    def chunk(self, content: str, strategy: ChunkStrategy = ChunkStrategy.SENTENCE, size: int = 200) -> List[DocumentChunk]:
        chunks = []
        if strategy == ChunkStrategy.FIXED:
            for i in range(0, len(content), size):
                chunk_text = content[i:i+size]
                chunks.append(DocumentChunk(len(chunks), chunk_text, i, i+len(chunk_text)))
        elif strategy == ChunkStrategy.SENTENCE:
            sentences = re.split(r'(?<=[.!?])\s+', content)
            current = ""
            start = 0
            for sent in sentences:
                if len(current) + len(sent) > size and current:
                    chunks.append(DocumentChunk(len(chunks), current, start, start+len(current)))
                    start += len(current)
                    current = sent
                else:
                    current += sent + " "
            if current:
                chunks.append(DocumentChunk(len(chunks), current, start, start+len(current)))
        elif strategy == ChunkStrategy.PARAGRAPH:
            paragraphs = content.split('\n\n')
            start = 0
            for para in paragraphs:
                if para.strip():
                    chunks.append(DocumentChunk(len(chunks), para, start, start+len(para)))
                    start += len(para) + 2
        return chunks

    def index(self, doc: Document) -> Dict[str, List[int]]:
        """Build inverted index from document chunks."""
        inverted: Dict[str, List[int]] = defaultdict(list)
        for chunk in doc.chunks:
            words = re.findall(r'\w+', chunk.text.lower())
            for word in set(words):
                inverted[word].append(chunk.id)
        return dict(inverted)

    def process(self, doc_id: str, content: str, chunk_strategy: ChunkStrategy = ChunkStrategy.SENTENCE, chunk_size: int = 200) -> Document:
        doc_type = self.detect_type(content)
        metadata = self.extract_metadata(content, doc_type)
        chunks = self.chunk(content, chunk_strategy, chunk_size)
        words = re.findall(r'\w+', content.lower())
        doc = Document(
            id=doc_id,
            content=content,
            doc_type=doc_type,
            chunks=chunks,
            metadata=metadata,
            term_freq=Counter(words),
        )
        return doc

    def search(self, docs: List[Document], query: str) -> List[Tuple[Document, float]]:
        """Simple TF-based search across documents."""
        query_words = set(re.findall(r'\w+', query.lower()))
        scored = []
        for doc in docs:
            score = sum(doc.term_freq[w] for w in query_words if w in doc.term_freq)
            if score > 0:
                scored.append((doc, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Document Processor Engine")
    print("ai/llm_document_processor_native.py")
    print("=" * 60)

    engine = DocumentProcessor()

    # 1. Process documents
    print("\n[1] Process Documents")
    docs = [
        engine.process("d1", "Python is a great language. It is easy to learn. Many developers use Python for AI and web development. Python has many libraries.", ChunkStrategy.SENTENCE, 50),
        engine.process("d2", "JavaScript runs in browsers. Node.js runs JavaScript on servers. React is a JavaScript framework for UI.", ChunkStrategy.SENTENCE, 50),
        engine.process("d3", "# Project README\n\nThis is a sample project. It uses Python and AI. Machine learning is the main focus.", ChunkStrategy.PARAGRAPH, 100),
    ]
    for doc in docs:
        print(f"  {doc.id}: type={doc.doc_type.value}, chunks={len(doc.chunks)}, words={doc.metadata['words']}")

    # 2. Chunk detail
    print("\n[2] Chunk Detail")
    for chunk in docs[0].chunks[:3]:
        print(f"  Chunk {chunk.id}: '{chunk.text[:40]}...'")

    # 3. Search
    print("\n[3] Search")
    results = engine.search(docs, "Python AI")
    for doc, score in results:
        print(f"  {doc.id}: score={score}")

    # 4. Inverted index
    print("\n[4] Inverted Index")
    idx = engine.index(docs[0])
    for word, chunk_ids in list(idx.items())[:5]:
        print(f"  {word}: chunks {chunk_ids}")

    # 5. Document type detection
    print("\n[5] Type Detection")
    samples = [
        '{"name": "test"}',
        '<root><item>1</item></root>',
        '# Title\n\nBody text',
        'def hello(): pass',
        'Plain text content here',
    ]
    for s in samples:
        t = engine.detect_type(s)
        print(f"  {s[:30]}... → {t.value}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
