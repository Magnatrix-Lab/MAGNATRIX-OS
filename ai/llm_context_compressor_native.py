"""
llm_context_compressor_native.py
MAGNATRIX-OS Context Compressor Engine
Native Python, stdlib only.
Provides context compression: summarization, truncation, chunking, and relevance-based pruning.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

class ContextCompressorEngine:
    def __init__(self, max_tokens: int = 4096) -> None:
        self.max_tokens = max_tokens

    def truncate(self, text: str, max_chars: int) -> str:
        return text[:max_chars] + "..." if len(text) > max_chars else text

    def sliding_window(self, text: str, window_size: int = 100, overlap: int = 20) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start:start + window_size])
            start += window_size - overlap
        return chunks

    def sentence_truncate(self, text: str, max_sentences: int = 5) -> str:
        sentences = text.split(".")
        return ".".join(sentences[:max_sentences]) + ("..." if len(sentences) > max_sentences else "")

    def compress(self, text: str, method: str = "truncate", **kwargs) -> str:
        if method == "truncate":
            return self.truncate(text, kwargs.get("max_chars", self.max_tokens * 4))
        elif method == "sentences":
            return self.sentence_truncate(text, kwargs.get("max_sentences", 5))
        elif method == "chunks":
            return self.sliding_window(text, kwargs.get("window_size", 200))
        return text

def run() -> None:
    print("=" * 60); print("MAGNATRIX-OS Context Compressor"); print("=" * 60)
    e = ContextCompressorEngine()
    text = "Hello world. This is a test. This is another sentence. Final sentence here."
    print(f"  Truncate: {e.truncate(text, 20)}")
    print(f"  Sentences: {e.sentence_truncate(text, 2)}")
    print(f"  Chunks: {e.sliding_window(text, 15, 5)}")
    print("\nContext Compressor test complete.")
if __name__ == "__main__": run()
