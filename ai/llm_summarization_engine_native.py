"""LLM Summarization Engine — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class SummarizationMethod(Enum):
    EXTRACTIVE = auto()
    ABLATIVE = auto()
    KEYPOINT = auto()

class SummarizationEngine:
    def __init__(self) -> None:
        self._stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "shall", "can", "need", "dare", "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into", "through", "during", "before", "after", "above", "below", "between", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just", "and", "but", "if", "or", "because", "until", "while", "about", "against", "up", "down", "out", "off", "over", "under", "again", "further", "then", "once"}

    def extractive(self, text: str, ratio: float = 0.3) -> str:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if not sentences:
            return ""
        scores = []
        for s in sentences:
            words = [w.lower() for w in re.findall(r'\w+', s) if w.lower() not in self._stopwords]
            scores.append(len(words))
        n = max(1, int(len(sentences) * ratio))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:n]
        ranked.sort(key=lambda x: x[0])
        return " ".join(sentences[i] for i, _ in ranked)

    def abstractive(self, text: str) -> str:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if not sentences:
            return ""
        words = []
        for s in sentences:
            words.extend(re.findall(r'\w+', s))
        freq = {}
        for w in words:
            w = w.lower()
            if w not in self._stopwords and len(w) > 3:
                freq[w] = freq.get(w, 0) + 1
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return "Key concepts: " + ", ".join(w for w, _ in top)

    def keypoints(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        points = []
        for s in sentences:
            if any(marker in s.lower() for marker in ["first", "second", "third", "important", "key", "main", "primary", "crucial", "essential"]):
                points.append(s)
        return points[:5]

    def summarize(self, text: str, method: SummarizationMethod = SummarizationMethod.EXTRACTIVE, ratio: float = 0.3) -> str:
        if method == SummarizationMethod.EXTRACTIVE:
            return self.extractive(text, ratio)
        elif method == SummarizationMethod.ABLATIVE:
            return self.abstractive(text)
        elif method == SummarizationMethod.KEYPOINT:
            return "\n".join("- " + p for p in self.keypoints(text))
        return ""

    def get_stats(self, text: str, summary: str) -> Dict[str, Any]:
        return {"original_tokens": len(text.split()), "summary_tokens": len(summary.split()), "compression": 1.0 - len(summary.split()) / len(text.split()) if text else 0.0}

def run() -> None:
    print("Summarization Engine test")
    e = SummarizationEngine()
    text = "The first important point is that AI is transforming industries. The second key idea is that ethical considerations are crucial. The third main concept is that human oversight remains essential. Some additional details are not as important but provide context."
    print("  Extractive: " + e.summarize(text, SummarizationMethod.EXTRACTIVE, 0.4))
    print("  Abstractive: " + e.summarize(text, SummarizationMethod.ABLATIVE))
    print("  Keypoints:")
    print(e.summarize(text, SummarizationMethod.KEYPOINT))
    print("Summarization Engine test complete.")

if __name__ == "__main__":
    run()
