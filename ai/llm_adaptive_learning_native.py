#!/usr/bin/env python3
"""
ai/llm_adaptive_learning_native.py
MAGNATRIX-OS — Adaptive Learning Engine for the LLM Arena
AMATI pattern: personalization, user modeling, style adaptation

Pure Python, stdlib only. Simulates user profiling, style adaptation,
topic preference learning, and skill estimation.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


# ───────────────────────────────────────────────────────────────
# 1. USER PROFILE
# ───────────────────────────────────────────────────────────────

@dataclass
class UserProfile:
    user_id: str
    style_preference: Dict[str, float] = field(default_factory=dict)  # concise, verbose, technical, simple
    topic_history: Dict[str, int] = field(default_factory=dict)
    skill_levels: Dict[str, float] = field(default_factory=dict)  # domain -> 0-1
    feedback_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = _now()
        if not self.style_preference:
            self.style_preference = {"concise": 0.5, "verbose": 0.5, "technical": 0.5, "simple": 0.5, "formal": 0.5, "casual": 0.5}


class UserProfileManager:
    """Track user preferences and interaction history."""

    def __init__(self) -> None:
        self._profiles: Dict[str, UserProfile] = {}

    def get_or_create(self, user_id: str) -> UserProfile:
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id)
        return self._profiles[user_id]

    def record_interaction(self, user_id: str, topic: str, query_length: int) -> None:
        profile = self.get_or_create(user_id)
        profile.topic_history[topic] = profile.topic_history.get(topic, 0) + 1
        # Estimate skill from query complexity
        if query_length < 20:
            profile.skill_levels.setdefault(topic, 0.3)
        elif query_length < 50:
            profile.skill_levels.setdefault(topic, 0.6)
        else:
            profile.skill_levels.setdefault(topic, 0.9)

    def record_feedback(self, user_id: str, rating: int, comment: str = "") -> None:
        profile = self.get_or_create(user_id)
        profile.feedback_history.append({"rating": rating, "comment": comment, "timestamp": _now()})
        # Adjust style based on feedback
        if rating >= 4:
            profile.style_preference["concise"] = min(1.0, profile.style_preference["concise"] + 0.05)
        elif rating <= 2:
            profile.style_preference["verbose"] = min(1.0, profile.style_preference["verbose"] + 0.05)

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        return self._profiles.get(user_id)


# ───────────────────────────────────────────────────────────────
# 2. STYLE ADAPTOR
# ───────────────────────────────────────────────────────────────

class StyleAdaptor:
    """Adapt response style based on user profile."""

    def adapt(self, response: str, profile: UserProfile) -> str:
        style = profile.style_preference
        adapted = response
        if style.get("concise", 0.5) > 0.7:
            adapted = self._make_concise(adapted)
        if style.get("technical", 0.5) > 0.7:
            adapted = self._make_technical(adapted)
        if style.get("simple", 0.5) > 0.7:
            adapted = self._make_simple(adapted)
        if style.get("formal", 0.5) > 0.7:
            adapted = self._make_formal(adapted)
        return adapted

    def _make_concise(self, text: str) -> str:
        sentences = text.split(". ")
        return ". ".join(sentences[:2]) + ("..." if len(sentences) > 2 else "")

    def _make_technical(self, text: str) -> str:
        return f"[TECHNICAL] {text}"

    def _make_simple(self, text: str) -> str:
        return f"[SIMPLE] {text}"

    def _make_formal(self, text: str) -> str:
        return f"[FORMAL] {text}"


# ───────────────────────────────────────────────────────────────
# 3. TOPIC PREFERENCE
# ───────────────────────────────────────────────────────────────

class TopicPreference:
    """Learn which topics user asks about and suggest related ones."""

    def __init__(self) -> None:
        self._topics: Dict[str, int] = {}

    def record(self, topic: str) -> None:
        self._topics[topic] = self._topics.get(topic, 0) + 1

    def get_top_topics(self, n: int = 5) -> List[Tuple[str, int]]:
        return sorted(self._topics.items(), key=lambda x: x[1], reverse=True)[:n]

    def suggest_related(self, topic: str) -> List[str]:
        related = {
            "coding": ["debugging", "testing", "algorithms", "system design"],
            "math": ["statistics", "linear algebra", "calculus", "probability"],
            "writing": ["editing", "grammar", "storytelling", "copywriting"],
            "ai": ["machine learning", "deep learning", "NLP", "computer vision"],
        }
        return related.get(topic, ["general", "tutorial", "reference"])


# ───────────────────────────────────────────────────────────────
# 4. SKILL ESTIMATOR
# ───────────────────────────────────────────────────────────────

class SkillEstimator:
    """Estimate user skill level per domain."""

    def estimate(self, query: str, domain: str) -> float:
        # Estimate based on query complexity
        words = len(query.split())
        technical_terms = sum(1 for w in ["algorithm", "function", "class", "API", "model", "architecture"] if w.lower() in query.lower())
        score = min(1.0, (words / 100) + (technical_terms / 10))
        return round(score, 2)

    def adjust_depth(self, response: str, skill: float) -> str:
        if skill < 0.3:
            return f"[BEGINNER] {response}"
        elif skill < 0.7:
            return f"[INTERMEDIATE] {response}"
        return f"[ADVANCED] {response}"


# ───────────────────────────────────────────────────────────────
# 5. FEEDBACK LEARNER
# ───────────────────────────────────────────────────────────────

class FeedbackLearner:
    """Learn from user feedback to improve future responses."""

    def __init__(self) -> None:
        self._patterns: Dict[str, List[int]] = {}

    def learn(self, context: str, rating: int) -> None:
        key = context[:20]
        self._patterns.setdefault(key, []).append(rating)

    def predict_quality(self, context: str) -> float:
        key = context[:20]
        ratings = self._patterns.get(key, [3])
        return round(sum(ratings) / len(ratings), 2)


# ───────────────────────────────────────────────────────────────
# 6. PERSONALIZATION ENGINE
# ───────────────────────────────────────────────────────────────

class PersonalizationEngine:
    """Apply all adaptations to generated responses."""

    def __init__(self) -> None:
        self.style = StyleAdaptor()
        self.topics = TopicPreference()
        self.skills = SkillEstimator()
        self.feedback = FeedbackLearner()

    def personalize(self, user_id: str, query: str, response: str, profile_manager: UserProfileManager) -> Dict[str, Any]:
        profile = profile_manager.get_or_create(user_id)

        # Detect topic
        topic = self._detect_topic(query)
        self.topics.record(topic)
        profile_manager.record_interaction(user_id, topic, len(query))

        # Style adaptation
        adapted = self.style.adapt(response, profile)

        # Skill-based depth adjustment
        skill = self.skills.estimate(query, topic)
        adapted = self.skills.adjust_depth(adapted, skill)
        profile.skill_levels[topic] = skill

        # Topic suggestions
        suggestions = self.topics.suggest_related(topic)

        return {
            "user_id": user_id,
            "original": response,
            "personalized": adapted,
            "topic": topic,
            "skill_level": skill,
            "suggestions": suggestions,
            "style_profile": profile.style_preference,
        }

    def _detect_topic(self, query: str) -> str:
        text = query.lower()
        if any(w in text for w in ["code", "program", "function", "debug"]):
            return "coding"
        if any(w in text for w in ["math", "equation", "solve", "calculate"]):
            return "math"
        if any(w in text for w in ["write", "essay", "email", "story"]):
            return "writing"
        if any(w in text for w in ["ai", "model", "neural", "learning"]):
            return "ai"
        return "general"


# ───────────────────────────────────────────────────────────────
# 7. ADAPTIVE LEARNING ENGINE
# ───────────────────────────────────────────────────────────────

class AdaptiveLearningEngine:
    """Main orchestrator: profile -> adapt -> personalize -> feedback -> learn."""

    def __init__(self) -> None:
        self.profiles = UserProfileManager()
        self.personalization = PersonalizationEngine()

    def process(self, user_id: str, query: str, response: str) -> Dict[str, Any]:
        result = self.personalization.personalize(user_id, query, response, self.profiles)
        return result

    def feedback(self, user_id: str, rating: int, context: str = "") -> None:
        self.profiles.record_feedback(user_id, rating, context)
        self.personalization.feedback.learn(context, rating)

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        return self.profiles.get_profile(user_id)

    def stats(self) -> Dict[str, Any]:
        return {"users": len(self.profiles._profiles), "topics": self.personalization.topics._topics}


# ───────────────────────────────────────────────────────────────
# 8. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Adaptive Learning Engine Demo")
    print("=" * 60)

    engine = AdaptiveLearningEngine()

    user_id = "user_123"

    interactions = [
        ("How do I write a Python function?", "A Python function is defined with def."),
        ("Explain neural networks in detail with math.", "Neural networks use layers of neurons."),
        ("Write a short email to my boss.", "Use a professional greeting and clear subject."),
    ]

    for i, (query, response) in enumerate(interactions, 1):
        print(f"\n[{i}] Query: {query}")
        result = engine.process(user_id, query, response)
        print(f"  Topic: {result['topic']}")
        print(f"  Skill: {result['skill_level']}")
        print(f"  Personalized: {result['personalized'][:80]}...")
        print(f"  Suggestions: {result['suggestions'][:2]}")

    # Feedback
    engine.feedback(user_id, 5, "Great explanation!")
    engine.feedback(user_id, 2, "Too verbose.")

    print(f"\n[PROFILE] {json.dumps(engine.get_user_profile(user_id).style_preference, indent=2)}")

    print(f"\n[STATS] {json.dumps(engine.stats(), indent=2)}")

    print("\n" + "=" * 60)
    print("Demo complete. Adaptive Learning Engine ready for LLM Arena.")
    print("=" * 60)
