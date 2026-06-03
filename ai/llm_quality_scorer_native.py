"""LLM Quality Scorer — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class QualityMetric(Enum):
    PERPLEXITY = auto()
    DIVERSITY = auto()
    READABILITY = auto()
    LENGTH = auto()

@dataclass
class QualityScore:
    metric: QualityMetric
    value: float
    normalized: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class QualityScorer:
    def __init__(self) -> None:
        self._weights: Dict[QualityMetric, float] = {
            QualityMetric.PERPLEXITY: 0.25,
            QualityMetric.DIVERSITY: 0.25,
            QualityMetric.READABILITY: 0.25,
            QualityMetric.LENGTH: 0.25,
        }

    def set_weight(self, metric: QualityMetric, weight: float) -> None:
        self._weights[metric] = weight

    def score_perplexity(self, text: str) -> float:
        words = text.split()
        if not words:
            return 0.0
        unique = len(set(words))
        return unique / len(words)

    def score_diversity(self, text: str) -> float:
        words = text.lower().split()
        if not words:
            return 0.0
        total = len(words)
        counts = {}
        for w in words:
            counts[w] = counts.get(w, 0) + 1
        entropy = -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)
        return min(entropy / 5.0, 1.0)

    def score_readability(self, text: str) -> float:
        sentences = text.split(".")
        words = text.split()
        if not sentences or not words:
            return 0.0
        avg_len = len(words) / len(sentences)
        return max(0.0, min(1.0, 1.0 - (avg_len - 15.0) / 30.0))

    def score_length(self, text: str) -> float:
        words = len(text.split())
        return min(words / 100.0, 1.0)

    def evaluate(self, text: str) -> List[QualityScore]:
        scores = [
            QualityScore(QualityMetric.PERPLEXITY, self.score_perplexity(text), self.score_perplexity(text)),
            QualityScore(QualityMetric.DIVERSITY, self.score_diversity(text), self.score_diversity(text)),
            QualityScore(QualityMetric.READABILITY, self.score_readability(text), self.score_readability(text)),
            QualityScore(QualityMetric.LENGTH, self.score_length(text), self.score_length(text)),
        ]
        return scores

    def weighted_score(self, scores: List[QualityScore]) -> float:
        total = 0.0
        weight_sum = 0.0
        for s in scores:
            w = self._weights.get(s.metric, 0.0)
            total += s.normalized * w
            weight_sum += w
        return total / weight_sum if weight_sum > 0 else 0.0

    def get_stats(self, scores: List[QualityScore]) -> Dict[str, Any]:
        return {"metrics": len(scores), "weighted": self.weighted_score(scores), "min": min(s.normalized for s in scores), "max": max(s.normalized for s in scores)}

def run() -> None:
    print("Quality Scorer test")
    e = QualityScorer()
    text = "The quick brown fox jumps over the lazy dog. This sentence is a pangram. It contains every letter of the alphabet at least once."
    scores = e.evaluate(text)
    for s in scores:
        print("  " + s.metric.name + ": " + str(s.normalized))
    print("  Weighted: " + str(e.weighted_score(scores)))
    print("  Stats: " + str(e.get_stats(scores)))
    print("Quality Scorer test complete.")

if __name__ == "__main__":
    run()
