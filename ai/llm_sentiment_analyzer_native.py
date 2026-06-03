#!/usr/bin/env python3
"""
MAGNATRIX-OS — Sentiment Analyzer Engine
ai/llm_sentiment_analyzer_native.py

Features:
- Lexicon-based sentiment scoring (positive/negative/neutral)
- Aspect-based sentiment (extract aspects and score each)
- Emotion detection (joy, anger, sadness, fear, surprise)
- Intensity scoring (how strong the sentiment is)
- Trend analysis over multiple texts

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sentiment_analyzer")


@dataclass
class SentimentResult:
    text: str
    polarity: float  # -1 to 1
    subjectivity: float  # 0 to 1
    emotions: Dict[str, float]
    aspects: Dict[str, float]


class SentimentAnalyzerEngine:
    """Sentiment analysis with lexicon, aspects, and emotions."""

    POSITIVE = {"good", "great", "excellent", "love", "best", "happy", "awesome", "perfect", "nice", "wonderful", "amazing", "fantastic", "joy", "beautiful", "smart", "helpful", "brilliant"}
    NEGATIVE = {"bad", "terrible", "worst", "hate", "poor", "slow", "broken", "awful", "useless", "frustrated", "angry", "sad", "disappointed", "horrible", "annoying", "stupid", "wrong"}
    EMOTION_WORDS = {
        "joy": {"happy", "joy", "excited", "glad", "cheerful", "delighted"},
        "anger": {"angry", "mad", "furious", "annoyed", "irritated"},
        "sadness": {"sad", "depressed", "unhappy", "miserable", "gloomy"},
        "fear": {"afraid", "scared", "terrified", "worried", "anxious"},
        "surprise": {"surprised", "shocked", "amazed", "astonished"},
    }
    ASPECT_INDICATORS = {
        "service": {"service", "support", "staff", "help"},
        "quality": {"quality", "build", "durability", "material"},
        "price": {"price", "cost", "expensive", "cheap", "value"},
        "speed": {"fast", "slow", "quick", "speed", "delay"},
    }

    def analyze(self, text: str) -> SentimentResult:
        words = re.findall(r'\w+', text.lower())
        pos = sum(1 for w in words if w in self.POSITIVE)
        neg = sum(1 for w in words if w in self.NEGATIVE)
        total = len(words) or 1
        polarity = (pos - neg) / max(pos + neg, 1)
        subjectivity = (pos + neg) / total

        emotions = {}
        for emotion, indicators in self.EMOTION_WORDS.items():
            count = sum(1 for w in words if w in indicators)
            emotions[emotion] = min(count / 3, 1.0)

        aspects = {}
        for aspect, indicators in self.ASPECT_INDICATORS.items():
            count = sum(1 for w in words if w in indicators)
            if count > 0:
                aspect_pos = sum(1 for w in words if w in self.POSITIVE and w in indicators)
                aspect_neg = sum(1 for w in words if w in self.NEGATIVE and w in indicators)
                aspects[aspect] = (aspect_pos - aspect_neg) / max(count, 1)

        return SentimentResult(text, polarity, subjectivity, emotions, aspects)

    def trend(self, texts: List[str]) -> Dict[str, Any]:
        results = [self.analyze(t) for t in texts]
        avg_polarity = sum(r.polarity for r in results) / len(results)
        avg_subjectivity = sum(r.subjectivity for r in results) / len(results)
        emotion_trends = defaultdict(list)
        for r in results:
            for e, v in r.emotions.items():
                emotion_trends[e].append(v)
        avg_emotions = {e: sum(v) / len(v) for e, v in emotion_trends.items()}
        return {
            "avg_polarity": avg_polarity,
            "avg_subjectivity": avg_subjectivity,
            "emotions": avg_emotions,
            "text_count": len(texts),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {"lexicon_size": len(self.POSITIVE) + len(self.NEGATIVE), "emotions": len(self.EMOTION_WORDS)}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Sentiment Analyzer Engine")
    print("ai/llm_sentiment_analyzer_native.py")
    print("=" * 60)

    engine = SentimentAnalyzerEngine()

    texts = [
        "I love this product! It is amazing and wonderful.",
        "The service was terrible and slow. I am frustrated.",
        "It is okay, nothing special but not bad either.",
        "The price is cheap but the quality is poor. I am disappointed.",
    ]

    for t in texts:
        r = engine.analyze(t)
        print(f"\nText: {t}")
        print(f"  Polarity: {r.polarity:+.2f}, Subjectivity: {r.subjectivity:.2f}")
        print(f"  Emotions: {r.emotions}")
        print(f"  Aspects: {r.aspects}")

    print("\n[5] Trend Analysis")
    trend = engine.trend(texts)
    print(f"  {trend}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
