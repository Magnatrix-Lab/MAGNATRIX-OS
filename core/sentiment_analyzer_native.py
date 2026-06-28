#!/usr/bin/env python3
"""Sentiment Analyzer for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

class SentimentAnalyzer:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.positive_words = {"good", "great", "excellent", "amazing", "happy", "love", "best", "perfect", "awesome"}
        self.negative_words = {"bad", "terrible", "awful", "hate", "worst", "horrible", "disappointing", "poor", "sad"}
        self.emotions = {"joy": {"happy", "joy", "excited"}, "anger": {"angry", "furious", "mad"}, "fear": {"scared", "afraid", "worried"}}
    def analyze(self, text: str) -> Dict[str, Any]:
        words = text.lower().split()
        pos = sum(1 for w in words if w in self.positive_words)
        neg = sum(1 for w in words if w in self.negative_words)
        total = pos + neg
        if total == 0:
            return {"polarity": "neutral", "score": 0.0, "emotions": {}}
        score = (pos - neg) / total
        polarity = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
        emotions = {k: sum(1 for w in words if w in v) for k, v in self.emotions.items()}
        return {"polarity": polarity, "score": round(score, 2), "emotions": emotions}
    def to_dict(self): return {"positive_words": len(self.positive_words), "negative_words": len(self.negative_words)}
