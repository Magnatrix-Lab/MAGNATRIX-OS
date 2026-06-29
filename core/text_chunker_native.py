"""
text_chunker_native.py
MAGNATRIX-OS — Text Chunker

Inspired by ai-knowledge-graph: Split large documents into manageable chunks with overlap. Pure stdlib.
"""

import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict


@dataclass
class Chunk:
    chunk_id: str
    text: str
    start_index: int
    end_index: int
    word_count: int


class TextChunker:
    """Split large documents into manageable chunks with overlap."""

    def __init__(self, chunk_size: int = 200, overlap: int = 20):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[Chunk]:
        """Split text into chunks with overlap."""
        words = text.split()
        chunks = []
        start = 0
        chunk_idx = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)
            chunks.append(Chunk(
                chunk_id=f"chunk_{chunk_idx}", text=chunk_text,
                start_index=start, end_index=end, word_count=len(chunk_words),
            ))
            start = end - self.overlap if end < len(words) else end
            chunk_idx += 1
        return chunks

    def chunk_by_sentences(self, text: str, sentences_per_chunk: int = 5) -> List[Chunk]:
        """Chunk by sentences instead of words."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        start = 0
        chunk_idx = 0
        while start < len(sentences):
            end = min(start + sentences_per_chunk, len(sentences))
            chunk_text = " ".join(sentences[start:end])
            word_count = len(chunk_text.split())
            chunks.append(Chunk(
                chunk_id=f"chunk_{chunk_idx}", text=chunk_text,
                start_index=start, end_index=end, word_count=word_count,
            ))
            start = end
            chunk_idx += 1
        return chunks

    def get_stats(self, chunks: List[Chunk]) -> dict:
        total_words = sum(c.word_count for c in chunks)
        avg = total_words / max(1, len(chunks))
        return {"chunks": len(chunks), "total_words": total_words, "avg_words_per_chunk": round(avg, 2)}

    def to_dict(self) -> dict:
        return {"chunk_size": self.chunk_size, "overlap": self.overlap}


__all__ = ["TextChunker", "Chunk"]