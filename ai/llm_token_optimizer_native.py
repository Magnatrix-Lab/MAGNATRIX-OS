"""LLM Token Optimizer — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Dict, Any, List

class TokenOptimizer:
    def __init__(self) -> None:
        self._stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "shall", "can", "need", "dare", "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into", "through", "during", "before", "after", "above", "below", "between", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just", "and", "but", "if", "or", "because", "until", "while", "about", "against", "up", "down", "out", "off", "over", "under", "again", "further", "then", "once"}

    def compress(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        words = text.split()
        compressed = [w for w in words if w.lower() not in self._stopwords or len(w) > 6]
        return " ".join(compressed)

    def deduplicate(self, text: str) -> str:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        seen = set()
        unique = []
        for s in sentences:
            normalized = re.sub(r'\s+', ' ', s.lower().strip())
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(s)
        return " ".join(unique)

    def optimize(self, text: str) -> str:
        return self.deduplicate(self.compress(text))

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def get_stats(self, text: str) -> Dict[str, Any]:
        original = self.count_tokens(text)
        optimized = self.optimize(text)
        optimized_count = self.count_tokens(optimized)
        return {"original_tokens": original, "optimized_tokens": optimized_count, "reduction": original - optimized_count}

def run() -> None:
    print("Token Optimizer test")
    e = TokenOptimizer()
    text = "The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog. This is a test of the deduplication system."
    stats = e.get_stats(text)
    print("  Stats: " + str(stats))
    print("Token Optimizer test complete.")

if __name__ == "__main__":
    run()
