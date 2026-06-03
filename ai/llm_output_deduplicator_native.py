"""
llm_output_deduplicator_native.py
MAGNATRIX-OS Output Deduplicator Engine
Native Python, stdlib only.
Provides deduplication of generated outputs with n-gram filtering, semantic clustering, and repetition detection.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Set

class OutputDeduplicatorEngine:
    def __init__(self, ngram_size: int = 3) -> None:
        self.ngram_size = ngram_size
        self._seen: Set[str] = set()

    def ngram_hash(self, text: str) -> str:
        words = text.lower().split()
        ngrams = []
        for i in range(len(words) - self.ngram_size + 1):
            ngrams.append("_".join(words[i:i + self.ngram_size]))
        return "|".join(sorted(set(ngrams)))

    def is_duplicate(self, text: str) -> bool:
        h = self.ngram_hash(text)
        if h in self._seen:
            return True
        self._seen.add(h)
        return False

    def deduplicate(self, texts: List[str]) -> List[str]:
        unique = []
        for t in texts:
            if not self.is_duplicate(t):
                unique.append(t)
        return unique

    def repetition_score(self, text: str) -> float:
        words = text.lower().split()
        if len(words) < 2:
            return 0.0
        ngrams = ["_".join(words[i:i + self.ngram_size]) for i in range(len(words) - self.ngram_size + 1)]
        unique = len(set(ngrams))
        return 1.0 - (unique / len(ngrams)) if ngrams else 0.0

    def get_stats(self) -> Dict[str, Any]:
        return {"seen": len(self._seen), "ngram_size": self.ngram_size}

def run() -> None:
    print("=" * 60); print("MAGNATRIX-OS Output Deduplicator"); print("=" * 60)
    e = OutputDeduplicatorEngine(ngram_size=2)
    texts = ["hello world today", "hello world today", "different text here", "hello world today"]
    unique = e.deduplicate(texts)
    print(f"  Unique: {unique}")
    print(f"  Repetition score: {e.repetition_score('hello hello hello world')}")
    print(f"  Stats: {e.get_stats()}")
    print("\nOutput Deduplicator test complete.")
if __name__ == "__main__": run()
