#!/usr/bin/env python3
"""
MAGNATRIX-OS — Summarization Engine
ai/llm_summarization_engine_native.py

Features:
- Extractive summarization (top N sentences by score)
- Sentence importance scoring (TF-IDF based)
- Abstractive summarization simulation (key phrase extraction + reassembly)
- Length control (max words, max sentences)
- Multi-document summarization

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("summarization")


class SummarizationEngine:
    """Extractive and abstractive summarization."""

    STOP_WORDS = {"the", "a", "is", "are", "was", "were", "to", "of", "and", "in", "that", "it", "for", "on", "with", "as", "this", "but", "or", "an", "be", "i", "you", "he", "she", "we", "they"}

    def _sentences(self, text: str) -> List[str]:
        return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

    def _word_freq(self, text: str) -> Counter:
        words = [w.lower() for w in re.findall(r'\w+', text) if w.lower() not in self.STOP_WORDS]
        return Counter(words)

    def extractive(self, text: str, num_sentences: int = 3) -> str:
        sentences = self._sentences(text)
        if len(sentences) <= num_sentences:
            return text
        word_freq = self._word_freq(text)
        scores = []
        for sent in sentences:
            words = [w.lower() for w in re.findall(r'\w+', sent)]
            score = sum(word_freq.get(w, 0) for w in words) / max(len(words), 1)
            scores.append((score, sent))
        scores.sort(key=lambda x: x[0], reverse=True)
        top = [s for _, s in scores[:num_sentences]]
        # Reorder by original position
        ordered = sorted(top, key=lambda s: text.index(s))
        return " ".join(ordered)

    def abstractive(self, text: str, max_words: int = 50) -> str:
        freq = self._word_freq(text)
        top_words = [w for w, _ in freq.most_common(10)]
        sentences = self._sentences(text)
        if not sentences:
            return ""
        # Take first sentence + key phrases
        first = sentences[0]
        phrases = ", ".join(top_words[:5])
        result = f"{first} Key points: {phrases}."
        words = result.split()
        if len(words) > max_words:
            result = " ".join(words[:max_words]) + "..."
        return result

    def multi_doc(self, texts: List[str], num_sentences: int = 2) -> str:
        combined = " ".join(texts)
        return self.extractive(combined, num_sentences)

    def get_stats(self) -> Dict[str, Any]:
        return {"engine": "SummarizationEngine", "modes": ["extractive", "abstractive", "multi_doc"]}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Summarization Engine")
    print("ai/llm_summarization_engine_native.py")
    print("=" * 60)

    engine = SummarizationEngine()

    text = """Python is a high-level programming language. It is widely used for web development, data science, and artificial intelligence. Python has a simple syntax that makes it easy to learn. Many developers prefer Python for its readability and extensive libraries. Machine learning frameworks like TensorFlow and PyTorch are built with Python. The language continues to grow in popularity."""

    print(f"\nOriginal ({len(text.split())} words):\n{text[:100]}...")

    print("\n[1] Extractive Summary")
    summary = engine.extractive(text, num_sentences=2)
    print(f"  {summary}")

    print("\n[2] Abstractive Summary")
    summary = engine.abstractive(text, max_words=30)
    print(f"  {summary}")

    print("\n[3] Multi-Document Summary")
    docs = [
        "Python is popular for AI. It has many libraries.",
        "JavaScript runs in browsers. React is a framework.",
        "Go is fast and compiled. It is used for microservices.",
    ]
    summary = engine.multi_doc(docs, num_sentences=2)
    print(f"  {summary}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
