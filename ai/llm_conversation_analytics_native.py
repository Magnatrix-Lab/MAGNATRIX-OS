#!/usr/bin/env python3
"""
MAGNATRIX-OS — Conversation Analytics Engine
ai/llm_conversation_analytics_native.py

Features:
- Sentiment tracking (positive/negative/neutral per message)
- Topic extraction (keyword frequency, trending topics)
- Engagement metrics (turn count, response time, length)
- Conversation quality scoring (coherence, relevance, depth)
- Analytics dashboard data generation

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("conversation_analytics")


class Sentiment(enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class Message:
    id: str
    role: str  # user / assistant
    text: str
    timestamp: float


@dataclass
class SentimentScore:
    label: Sentiment
    confidence: float
    keywords: List[str] = field(default_factory=list)


@dataclass
class ConversationMetrics:
    total_messages: int
    user_messages: int
    assistant_messages: int
    avg_response_time: float
    avg_message_length: float
    sentiment_distribution: Dict[str, int]
    top_topics: List[Tuple[str, int]]
    quality_score: float
    engagement_score: float


class SentimentAnalyzer:
    """Simple rule-based sentiment analysis."""

    POSITIVE = ["good", "great", "excellent", "love", "best", "happy", "thanks", "awesome", "perfect", "nice", "helpful", "amazing"]
    NEGATIVE = ["bad", "terrible", "worst", "hate", "poor", "slow", "broken", "error", "bug", "awful", "useless", "frustrated"]

    def analyze(self, text: str) -> SentimentScore:
        words = re.findall(r'\w+', text.lower())
        pos = sum(1 for w in words if w in self.POSITIVE)
        neg = sum(1 for w in words if w in self.NEGATIVE)
        total = len(words) or 1

        pos_kw = [w for w in words if w in self.POSITIVE]
        neg_kw = [w for w in words if w in self.NEGATIVE]

        if pos > neg:
            return SentimentScore(Sentiment.POSITIVE, min(pos / total, 1.0), pos_kw)
        elif neg > pos:
            return SentimentScore(Sentiment.NEGATIVE, min(neg / total, 1.0), neg_kw)
        return SentimentScore(Sentiment.NEUTRAL, 0.5, [])


class TopicExtractor:
    """Extract topics from conversation."""

    STOP_WORDS = ["the", "a", "is", "are", "was", "were", "to", "of", "and", "in", "that", "it", "for", "on", "with", "as", "this", "but", "or", "an", "be", "i", "you", "he", "she", "we", "they", "me", "him", "her", "us", "them"]

    def extract(self, messages: List[Message]) -> Counter:
        all_words = []
        for msg in messages:
            words = re.findall(r'\w+', msg.text.lower())
            all_words.extend([w for w in words if w not in self.STOP_WORDS and len(w) > 3])
        return Counter(all_words)


class ConversationAnalyticsEngine:
    """Unified conversation analytics."""

    def __init__(self):
        self.sentiment = SentimentAnalyzer()
        self.topic = TopicExtractor()
        self._conversations: Dict[str, List[Message]] = defaultdict(list)

    def add_message(self, conversation_id: str, message: Message) -> None:
        self._conversations[conversation_id].append(message)

    def analyze(self, conversation_id: str) -> ConversationMetrics:
        messages = self._conversations.get(conversation_id, [])
        if not messages:
            return ConversationMetrics(0, 0, 0, 0, 0, {}, [], 0, 0)

        # Sentiment
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        for msg in messages:
            score = self.sentiment.analyze(msg.text)
            sentiments[score.label.value] += 1

        # Topics
        topics = self.topic.extract(messages)
        top_topics = topics.most_common(5)

        # Response times (assistant after user)
        response_times = []
        for i in range(1, len(messages)):
            if messages[i].role == "assistant" and messages[i-1].role == "user":
                response_times.append(messages[i].timestamp - messages[i-1].timestamp)
        avg_response = sum(response_times) / max(len(response_times), 1)

        # Lengths
        avg_length = sum(len(m.text) for m in messages) / len(messages)

        # Quality score (heuristic: longer + coherent + relevant)
        quality = min(avg_length / 100, 1.0) * 0.4 + min(len(messages) / 20, 1.0) * 0.3 + (1.0 if sentiments["positive"] > sentiments["negative"] else 0.5) * 0.3

        # Engagement (turn count + back-and-forth)
        turns = sum(1 for i in range(1, len(messages)) if messages[i].role != messages[i-1].role)
        engagement = min(turns / 10, 1.0) * 0.5 + min(len(messages) / 20, 1.0) * 0.5

        return ConversationMetrics(
            total_messages=len(messages),
            user_messages=sum(1 for m in messages if m.role == "user"),
            assistant_messages=sum(1 for m in messages if m.role == "assistant"),
            avg_response_time=avg_response,
            avg_message_length=avg_length,
            sentiment_distribution=sentiments,
            top_topics=top_topics,
            quality_score=quality,
            engagement_score=engagement,
        )

    def get_dashboard(self, conversation_id: str) -> Dict[str, Any]:
        metrics = self.analyze(conversation_id)
        return {
            "conversation_id": conversation_id,
            "summary": {
                "total_messages": metrics.total_messages,
                "turns": metrics.user_messages,
                "quality": f"{metrics.quality_score:.1%}",
                "engagement": f"{metrics.engagement_score:.1%}",
            },
            "sentiment": metrics.sentiment_distribution,
            "topics": [{"word": w, "count": c} for w, c in metrics.top_topics],
            "performance": {
                "avg_response_time": f"{metrics.avg_response_time:.2f}s",
                "avg_message_length": f"{metrics.avg_message_length:.0f} chars",
            },
        }

    def get_all_stats(self) -> Dict[str, Any]:
        return {
            "conversations": len(self._conversations),
            "total_messages": sum(len(msgs) for msgs in self._conversations.values()),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Conversation Analytics Engine")
    print("ai/llm_conversation_analytics_native.py")
    print("=" * 60)

    engine = ConversationAnalyticsEngine()
    conv_id = "conv-001"

    # Simulate conversation
    messages = [
        Message("m1", "user", "Hello! I need help with my Python code. It's running very slow.", 0.0),
        Message("m2", "assistant", "I'd be happy to help! Can you share the code snippet that's slow?", 2.0),
        Message("m3", "user", "Here it is: a loop that processes 10000 items. Thanks for the quick response!", 5.0),
        Message("m4", "assistant", "You can use list comprehension or vectorization with numpy. That would be much faster and more efficient.", 7.0),
        Message("m5", "user", "Great! I'll try that. This is amazing help, really helpful.", 12.0),
        Message("m6", "assistant", "Glad to help! Let me know if you need more optimization tips.", 14.0),
    ]
    for msg in messages:
        engine.add_message(conv_id, msg)

    # 1. Analyze
    print("[1] Conversation Analysis")
    metrics = engine.analyze(conv_id)
    print(f"  Messages: {metrics.total_messages} (user={metrics.user_messages}, assistant={metrics.assistant_messages})")
    print(f"  Sentiment: {metrics.sentiment_distribution}")
    print(f"  Quality: {metrics.quality_score:.1%}")
    print(f"  Engagement: {metrics.engagement_score:.1%}")
    print(f"  Avg response: {metrics.avg_response_time:.2f}s")
    print(f"  Avg length: {metrics.avg_message_length:.0f} chars")

    # 2. Topics
    print("[2] Top Topics")
    for word, count in metrics.top_topics:
        print(f"  {word}: {count}")

    # 3. Dashboard
    print("[3] Dashboard")
    dash = engine.get_dashboard(conv_id)
    print(f"  {dash['summary']}")
    print(f"  Performance: {dash['performance']}")

    # 4. Sentiment detail
    print("[4] Sentiment Per Message")
    for msg in messages:
        s = engine.sentiment.analyze(msg.text)
        print(f"  [{s.label.value}] {msg.text[:40]}... (conf={s.confidence:.2f})")

    # 5. Stats
    print("[5] Engine Stats")
    print(f"  {engine.get_all_stats()}")

    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
