"""Long Context Manager — Handle超长上下文 with sliding window, chunking, and retrieval.

Modul ini menyediakan:
- ContextChunker untuk split long text into chunks
- ContextWindow untuk sliding window management
- ContextCompressor untuk compress context via summarization
- ContextRetriever untuk retrieve relevant segments from long context
- LongContextManager untuk end-to-end超长context handling
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ChunkStrategy(Enum):
    FIXED = auto()
    SENTENCE = auto()
    PARAGRAPH = auto()
    TOKEN = auto()
    SEMANTIC = auto()


@dataclass
class ContextChunk:
    """Single chunk of context."""
    chunk_id: str
    text: str
    index: int
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 0.0

    def __post_init__(self):
        if self.token_count == 0:
            self.token_count = max(1, len(self.text) // 4)


@dataclass
class ContextWindow:
    """Sliding window over chunks."""
    window_id: str
    chunks: List[ContextChunk] = field(default_factory=list)
    max_tokens: int = 4096
    overlap: int = 100

    def total_tokens(self) -> int:
        return sum(c.token_count for c in self.chunks)

    def is_full(self) -> bool:
        return self.total_tokens() >= self.max_tokens

    def add_chunk(self, chunk: ContextChunk) -> bool:
        if self.total_tokens() + chunk.token_count > self.max_tokens:
            return False
        self.chunks.append(chunk)
        return True

    def slide(self, new_chunk: ContextChunk) -> Optional[ContextChunk]:
        """Add new chunk, remove oldest if needed."""
        removed = None
        while self.chunks and self.total_tokens() + new_chunk.token_count > self.max_tokens:
            removed = self.chunks.pop(0)
        self.chunks.append(new_chunk)
        return removed

    def get_text(self) -> str:
        return "\n".join(c.text for c in self.chunks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_id": self.window_id,
            "chunks": len(self.chunks),
            "total_tokens": self.total_tokens(),
            "max_tokens": self.max_tokens,
        }


class ContextChunker:
    """Split long text into chunks."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50, strategy: ChunkStrategy = ChunkStrategy.PARAGRAPH):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.strategy = strategy

    def chunk(self, text: str) -> List[ContextChunk]:
        if self.strategy == ChunkStrategy.FIXED:
            return self._chunk_fixed(text)
        elif self.strategy == ChunkStrategy.SENTENCE:
            return self._chunk_sentence(text)
        elif self.strategy == ChunkStrategy.PARAGRAPH:
            return self._chunk_paragraph(text)
        elif self.strategy == ChunkStrategy.TOKEN:
            return self._chunk_token(text)
        return self._chunk_fixed(text)

    def _chunk_fixed(self, text: str) -> List[ContextChunk]:
        chunks = []
        start = 0
        idx = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            chunks.append(ContextChunk(str(uuid.uuid4())[:8], chunk_text, idx))
            start = end - self.overlap
            idx += 1
        return chunks

    def _chunk_sentence(self, text: str) -> List[ContextChunk]:
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = []
        current_len = 0
        idx = 0
        for sent in sentences:
            if current_len + len(sent) > self.chunk_size and current:
                chunks.append(ContextChunk(str(uuid.uuid4())[:8], " ".join(current), idx))
                idx += 1
                current = current[-1:] if self.overlap > 0 else []
                current_len = sum(len(c) for c in current)
            current.append(sent)
            current_len += len(sent)
        if current:
            chunks.append(ContextChunk(str(uuid.uuid4())[:8], " ".join(current), idx))
        return chunks

    def _chunk_paragraph(self, text: str) -> List[ContextChunk]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current = []
        current_len = 0
        idx = 0
        for para in paragraphs:
            if current_len + len(para) > self.chunk_size and current:
                chunks.append(ContextChunk(str(uuid.uuid4())[:8], "\n\n".join(current), idx))
                idx += 1
                current = []
                current_len = 0
            current.append(para)
            current_len += len(para)
        if current:
            chunks.append(ContextChunk(str(uuid.uuid4())[:8], "\n\n".join(current), idx))
        return chunks

    def _chunk_token(self, text: str) -> List[ContextChunk]:
        # Approximate 1 token = 4 chars
        tokens = text.split()
        chunks = []
        current = []
        idx = 0
        for token in tokens:
            current.append(token)
            if len(" ".join(current)) >= self.chunk_size * 4:
                chunks.append(ContextChunk(str(uuid.uuid4())[:8], " ".join(current), idx))
                idx += 1
                current = current[-self.overlap:] if self.overlap > 0 else []
        if current:
            chunks.append(ContextChunk(str(uuid.uuid4())[:8], " ".join(current), idx))
        return chunks


class ContextCompressor:
    """Compress context via summarization."""

    def __init__(self, compression_ratio: float = 0.3):
        self.ratio = compression_ratio

    def compress(self, text: str, compressor_fn: Optional[Callable[[str], str]] = None) -> str:
        compressor_fn = compressor_fn or self._default_compressor
        return compressor_fn(text)

    def compress_chunks(self, chunks: List[ContextChunk], compressor_fn: Optional[Callable[[str], str]] = None) -> List[ContextChunk]:
        compressed = []
        for chunk in chunks:
            new_text = self.compress(chunk.text, compressor_fn)
            compressed.append(ContextChunk(
                chunk.chunk_id, new_text, chunk.index,
                metadata={**chunk.metadata, "compressed": True}
            ))
        return compressed

    def _default_compressor(self, text: str) -> str:
        # Extractive: keep first sentence of each paragraph
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        summary = []
        for para in paragraphs:
            sentences = para.split(".")
            if sentences:
                first = sentences[0].strip()
                if first:
                    summary.append(first + ".")
        return " ".join(summary)


class ContextRetriever:
    """Retrieve relevant segments from long context."""

    def __init__(self):
        self._index: Dict[str, ContextChunk] = {}

    def index(self, chunks: List[ContextChunk]) -> None:
        for chunk in chunks:
            self._index[chunk.chunk_id] = chunk

    def retrieve(self, query: str, top_k: int = 3) -> List[ContextChunk]:
        query_words = set(query.lower().split())
        scored = []
        for chunk in self._index.values():
            chunk_words = set(chunk.text.lower().split())
            overlap = len(query_words & chunk_words)
            score = overlap / max(len(query_words), 1)
            chunk.relevance_score = score
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    def retrieve_by_keyword(self, keywords: List[str], top_k: int = 3) -> List[ContextChunk]:
        keyword_set = set(k.lower() for k in keywords)
        scored = []
        for chunk in self._index.values():
            chunk_words = set(chunk.text.lower().split())
            overlap = len(keyword_set & chunk_words)
            score = overlap / max(len(keyword_set), 1)
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]


class LongContextManager:
    """End-to-end超长context handling."""

    def __init__(self, max_tokens: int = 8192, chunk_size: int = 500):
        self.max_tokens = max_tokens
        self.chunker = ContextChunker(chunk_size=chunk_size)
        self.compressor = ContextCompressor()
        self.retriever = ContextRetriever()
        self.window = ContextWindow(
            window_id="main",
            max_tokens=max_tokens,
            overlap=100,
        )
        self._chunks: List[ContextChunk] = []
        self._full_text = ""

    def load(self, text: str) -> List[ContextChunk]:
        self._full_text = text
        self._chunks = self.chunker.chunk(text)
        self.retriever.index(self._chunks)
        return self._chunks

    def get_window(self, query: Optional[str] = None) -> ContextWindow:
        if query:
            relevant = self.retriever.retrieve(query, top_k=5)
            self.window.chunks = relevant
        else:
            self.window.chunks = self._chunks[:10]
        return self.window

    def get_summary(self) -> str:
        return self.compressor.compress(self._full_text)

    def get_relevant(self, query: str, top_k: int = 3) -> List[ContextChunk]:
        return self.retriever.retrieve(query, top_k)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_chars": len(self._full_text),
            "total_chunks": len(self._chunks),
            "total_tokens": sum(c.token_count for c in self._chunks),
            "window_tokens": self.window.total_tokens(),
            "compression_ratio": len(self.get_summary()) / max(len(self._full_text), 1),
        }

    def export_chunks(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([{"id": c.chunk_id, "text": c.text[:100], "tokens": c.token_count} for c in self._chunks], f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("LONG CONTEXT MANAGER DEMO")
    print("=" * 70)

    long_text = """Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural intelligence displayed by animals including humans. AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.

The term artificial intelligence was coined in 1956. But it has become more popular today thanks to increased data volumes, advanced algorithms, and improvements in computing power and storage. In the early days of AI, researchers focused on symbolic reasoning and problem solving. The 1980s saw the rise of expert systems, which encoded human knowledge into rules.

Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed. Deep learning is a subset of machine learning that uses neural networks with many layers. These networks can learn complex patterns in large amounts of data.

Natural language processing (NLP) is another important area of AI. NLP enables computers to understand, interpret, and generate human language. Applications include chatbots, translation services, and sentiment analysis. Recent advances in NLP have been driven by transformer models like BERT and GPT.

Computer vision is the field of AI that enables computers to derive meaningful information from digital images, videos, and other visual inputs. Applications include facial recognition, autonomous driving, and medical image analysis. Convolutional neural networks (CNNs) are commonly used in computer vision tasks.

Robotics combines AI with mechanical engineering to create machines that can perform physical tasks. Robots are used in manufacturing, healthcare, and exploration. Advances in AI are enabling robots to perform more complex tasks with greater autonomy.

Ethics in AI is a growing concern. Issues include bias in algorithms, privacy concerns, and the potential for job displacement. Researchers and policymakers are working to develop guidelines for responsible AI development and deployment. The future of AI holds both great promise and significant challenges."""

    # 1. Load and chunk
    print(f"\n[1] Chunking (text: {len(long_text)} chars)")
    manager = LongContextManager(max_tokens=4096, chunk_size=300)
    chunks = manager.load(long_text)
    print(f"  Chunks: {len(chunks)}")
    for c in chunks[:3]:
        print(f"    {c.chunk_id}: {c.text[:50]}... (tokens={c.token_count})")

    # 2. Window management
    print("\n[2] Context Window")
    window = manager.get_window()
    print(f"  Window: {len(window.chunks)} chunks, {window.total_tokens()} tokens")
    print(f"  Text preview: {window.get_text()[:100]}...")

    # 3. Retrieval
    print("\n[3] Relevant Retrieval")
    relevant = manager.get_relevant("machine learning neural networks", top_k=2)
    print(f"  Query: 'machine learning neural networks'")
    for c in relevant:
        print(f"    [{c.relevance_score:.2f}] {c.text[:60]}...")

    # 4. Compression
    print("\n[4] Context Compression")
    summary = manager.get_summary()
    print(f"  Summary ({len(summary)} chars from {len(long_text)} chars):")
    print(f"    {summary[:150]}...")
    print(f"  Compression ratio: {len(summary)/len(long_text):.1%}")

    # 5. Keyword retrieval
    print("\n[5] Keyword Retrieval")
    kw_relevant = manager.retriever.retrieve_by_keyword(["ethics", "bias", "privacy"], top_k=2)
    for c in kw_relevant:
        print(f"    [{c.relevance_score:.2f}] {c.text[:60]}...")

    # 6. Sliding window
    print("\n[6] Sliding Window")
    sw = ContextWindow(window_id="slide", max_tokens=200, overlap=20)
    for c in chunks[:5]:
        added = sw.add_chunk(c)
        print(f"  Chunk {c.index}: added={added}, tokens={sw.total_tokens()}")
    # Slide
    new_chunk = ContextChunk("new", "New information added here." * 10, 99)
    removed = sw.slide(new_chunk)
    print(f"  After slide: {len(sw.chunks)} chunks, removed={removed.chunk_id if removed else 'None'}")

    # 7. Stats
    print(f"\n[7] Stats")
    print(f"  {manager.get_stats()}")

    # 8. Export
    print("\n[8] Export")
    manager.export_chunks("/tmp/context_chunks.json")
    print("  Exported to /tmp/context_chunks.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
