"""LLM Long Context Compressor — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

class LongContextCompressor:
    def __init__(self, max_tokens: int = 4096) -> None:
        self.max_tokens = max_tokens

    def estimate_tokens(self, text: str) -> int:
        return len(text.split())

    def _sentence_score(self, sentence: str, query: Optional[str] = None) -> float:
        score = 0.0
        if query:
            q_words = set(query.lower().split())
            s_words = set(sentence.lower().split())
            overlap = len(q_words & s_words)
            score += overlap / max(len(q_words), 1) * 2.0
        score += len(sentence.split()) * 0.05
        return score

    def compress(self, text: str, query: Optional[str] = None, target_ratio: float = 0.5) -> str:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if not sentences:
            return ""
        total_tokens = sum(self.estimate_tokens(s) for s in sentences)
        if total_tokens <= self.max_tokens * target_ratio:
            return text
        scored = [(i, self._sentence_score(s, query), s) for i, s in enumerate(sentences)]
        scored.sort(key=lambda x: x[1], reverse=True)
        target_tokens = int(total_tokens * target_ratio)
        selected = []
        current = 0
        for i, score, s in scored:
            tokens = self.estimate_tokens(s)
            if current + tokens <= target_tokens:
                selected.append((i, s))
                current += tokens
        selected.sort(key=lambda x: x[0])
        return " ".join(s for _, s in selected)

    def get_stats(self, original: str, compressed: str) -> Dict[str, Any]:
        return {"original_tokens": self.estimate_tokens(original), "compressed_tokens": self.estimate_tokens(compressed), "ratio": self.estimate_tokens(compressed) / self.estimate_tokens(original) if original else 0.0}

def run() -> None:
    print("Long Context Compressor test")
    e = LongContextCompressor(max_tokens=30)
    text = "Artificial intelligence is transforming the world. Machine learning enables computers to learn from data. Deep learning uses neural networks. Natural language processing helps machines understand text. Computer vision allows image recognition."
    compressed = e.compress(text, query="neural networks", target_ratio=0.4)
    print("  Compressed: " + compressed)
    print("  Stats: " + str(e.get_stats(text, compressed)))
    print("Long Context Compressor test complete.")

if __name__ == "__main__":
    run()
