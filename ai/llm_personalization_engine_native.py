#!/usr/bin/env python3
"""
MAGNATRIX-OS — Personalization Engine
ai/llm_personalization_engine_native.py

Features:
- User profile management (preferences, history, behavior)
- Preference learning (track likes/dislikes, adapt over time)
- Content recommendation scoring (relevance to user profile)
- Style adaptation (formal vs casual, detail level, tone)
- Personalized prompt template selection

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("personalization")


class StylePreference(enum.Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    CONCISE = "concise"
    DETAILED = "detailed"


@dataclass
class UserProfile:
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)
    liked_topics: List[str] = field(default_factory=list)
    disliked_topics: List[str] = field(default_factory=list)
    style: StylePreference = StylePreference.CASUAL
    detail_level: float = 0.5
    engagement_score: float = 0.0


@dataclass
class ContentItem:
    id: str
    text: str
    topics: List[str]
    difficulty: float
    style: StylePreference


class PersonalizationEngine:
    """User personalization and content adaptation."""

    def __init__(self):
        self._profiles: Dict[str, UserProfile] = {}
        self._interactions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def create_profile(self, user_id: str, **prefs) -> UserProfile:
        profile = UserProfile(user_id=user_id, **prefs)
        self._profiles[user_id] = profile
        return profile

    def record_interaction(self, user_id: str, content_id: str, feedback: str, topics: List[str]) -> None:
        self._interactions[user_id].append({"content": content_id, "feedback": feedback, "topics": topics})
        profile = self._profiles.get(user_id)
        if not profile:
            return
        if feedback == "like":
            profile.liked_topics.extend(t for t in topics if t not in profile.liked_topics)
        elif feedback == "dislike":
            profile.disliked_topics.extend(t for t in topics if t not in profile.disliked_topics)
        profile.engagement_score = min(len(self._interactions[user_id]) / 20, 1.0)

    def recommend(self, user_id: str, items: List[ContentItem], top_n: int = 3) -> List[Tuple[ContentItem, float]]:
        profile = self._profiles.get(user_id)
        if not profile:
            return [(item, 0.5) for item in items[:top_n]]
        scored = []
        for item in items:
            score = 0.0
            # Topic overlap with liked topics
            liked_overlap = len(set(item.topics) & set(profile.liked_topics))
            score += liked_overlap * 0.3
            # Penalize disliked topics
            disliked_overlap = len(set(item.topics) & set(profile.disliked_topics))
            score -= disliked_overlap * 0.5
            # Style match
            if item.style == profile.style:
                score += 0.2
            # Difficulty match (assume detail_level maps to preferred difficulty)
            score -= abs(item.difficulty - profile.detail_level) * 0.2
            scored.append((item, max(0.0, score)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_n]

    def adapt_prompt(self, user_id: str, base_prompt: str) -> str:
        profile = self._profiles.get(user_id)
        if not profile:
            return base_prompt
        modifiers = []
        if profile.style == StylePreference.FORMAL:
            modifiers.append("Use formal language and professional tone.")
        elif profile.style == StylePreference.CASUAL:
            modifiers.append("Use casual, conversational tone.")
        elif profile.style == StylePreference.TECHNICAL:
            modifiers.append("Include technical details and terminology.")
        if profile.detail_level > 0.7:
            modifiers.append("Provide detailed, comprehensive explanations.")
        elif profile.detail_level < 0.3:
            modifiers.append("Be concise and to the point.")
        if modifiers:
            return base_prompt + "\n\n[Preferences]\n" + "\n".join(modifiers)
        return base_prompt

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        return self._profiles.get(user_id)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "users": len(self._profiles),
            "total_interactions": sum(len(v) for v in self._interactions.values()),
            "avg_engagement": sum(p.engagement_score for p in self._profiles.values()) / max(len(self._profiles), 1),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Personalization Engine")
    print("ai/llm_personalization_engine_native.py")
    print("=" * 60)

    engine = PersonalizationEngine()

    # 1. Create profiles
    print("\n[1] Create User Profiles")
    engine.create_profile("alice", style=StylePreference.TECHNICAL, detail_level=0.9, liked_topics=["python", "ai"])
    engine.create_profile("bob", style=StylePreference.CASUAL, detail_level=0.3, liked_topics=["news", "sports"])
    print("  Created 2 profiles")

    # 2. Record interactions
    print("\n[2] Record Interactions")
    engine.record_interaction("alice", "c1", "like", ["python"])
    engine.record_interaction("alice", "c2", "like", ["ai", "ml"])
    engine.record_interaction("alice", "c3", "dislike", ["sports"])
    engine.record_interaction("bob", "c4", "like", ["sports"])
    print("  Recorded 4 interactions")

    # 3. Recommend
    print("\n[3] Content Recommendations")
    items = [
        ContentItem("i1", "Python tutorial", ["python", "coding"], 0.5, StylePreference.TECHNICAL),
        ContentItem("i2", "AI news", ["ai", "news"], 0.6, StylePreference.CASUAL),
        ContentItem("i3", "Sports update", ["sports"], 0.3, StylePreference.CASUAL),
        ContentItem("i4", "ML deep dive", ["ai", "ml"], 0.8, StylePreference.TECHNICAL),
    ]
    for user in ["alice", "bob"]:
        recs = engine.recommend(user, items, top_n=2)
        print(f"  {user}: {[f'{r[0].id}({r[1]:.2f})' for r in recs]}")

    # 4. Prompt adaptation
    print("\n[4] Prompt Adaptation")
    base = "Explain machine learning."
    for user in ["alice", "bob"]:
        adapted = engine.adapt_prompt(user, base)
        print(f"  {user}: {adapted[:100]}...")

    # 5. Stats
    print("\n[5] Engine Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
