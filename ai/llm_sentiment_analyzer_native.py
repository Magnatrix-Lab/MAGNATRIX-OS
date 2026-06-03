"""LLM Sentiment Analyzer — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class SentimentLabel(Enum):
    POSITIVE = auto()
    NEGATIVE = auto()
    NEUTRAL = auto()
    MIXED = auto()

class SentimentAnalyzer:
    def __init__(self) -> None:
        self._positive = {"good", "great", "excellent", "amazing", "love", "best", "happy", "wonderful", "fantastic", "awesome", "perfect", "brilliant", "outstanding", "superb", "delightful"}
        self._negative = {"bad", "terrible", "awful", "worst", "hate", "horrible", "disappointing", "poor", "sad", "angry", "frustrated", "annoying", "useless", "waste", "fail"}
        self._intensifiers = {"very", "extremely", "incredibly", "absolutely", "totally", "quite", "really", "so"}
        self._negations = {"not", "no", "never", "none", "nobody", "nothing", "neither", "nowhere", "hardly", "barely"}

    def analyze(self, text: str) -> Dict[str, Any]:
        words = re.findall(r'\b\w+\b', text.lower())
        pos_score = 0.0
        neg_score = 0.0
        negation_active = False
        intensity = 1.0
        for word in words:
            if word in self._negations:
                negation_active = True
                continue
            if word in self._intensifiers:
                intensity = 1.5
                continue
            if word in self._positive:
                score = intensity * (-1 if negation_active else 1)
                pos_score += max(score, 0)
                neg_score += max(-score, 0)
                negation_active = False
                intensity = 1.0
            elif word in self._negative:
                score = intensity * (-1 if negation_active else 1)
                neg_score += max(score, 0)
                pos_score += max(-score, 0)
                negation_active = False
                intensity = 1.0
        total = pos_score + neg_score
        if total == 0:
            label = SentimentLabel.NEUTRAL
        elif pos_score > neg_score * 1.5:
            label = SentimentLabel.POSITIVE
        elif neg_score > pos_score * 1.5:
            label = SentimentLabel.NEGATIVE
        else:
            label = SentimentLabel.MIXED
        return {"label": label.name, "positive": pos_score, "negative": neg_score, "score": (pos_score - neg_score) / total if total > 0 else 0.0}

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        return [self.analyze(t) for t in texts]

    def get_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        counts = {}
        for r in results:
            counts[r["label"]] = counts.get(r["label"], 0) + 1
        return {"total": len(results), "by_label": counts, "avg_score": sum(r["score"] for r in results) / len(results) if results else 0.0}

def run() -> None:
    print("Sentiment Analyzer test")
    e = SentimentAnalyzer()
    texts = ["This is amazing and wonderful!", "I hate this terrible product.", "It was ok, nothing special.", "Not bad at all, quite good actually."]
    results = e.analyze_batch(texts)
    for t, r in zip(texts, results):
        print("  '" + t + "' -> " + r["label"] + " (score: " + str(r["score"]) + ")")
    print("  Stats: " + str(e.get_stats(results)))
    print("Sentiment Analyzer test complete.")

if __name__ == "__main__":
    run()
