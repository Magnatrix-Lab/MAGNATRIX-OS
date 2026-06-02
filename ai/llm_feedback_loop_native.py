"""Feedback Loop (RLHF) — Collect human feedback, train reward models, and optimize responses.

Modul ini menyediakan:
- FeedbackCollector untuk collect ratings, comparisons, and corrections
- RewardModel untuk learn from feedback
- PreferenceDataset untuk manage preference pairs
- RLHFLoop untuk training loop
- FeedbackEngine untuk end-to-end RLHF pipeline
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class FeedbackType(Enum):
    RATING = auto()
    COMPARISON = auto()
    CORRECTION = auto()
    REJECTION = auto()


class FeedbackSource(Enum):
    HUMAN = auto()
    AUTOMATED = auto()
    HYBRID = auto()


@dataclass
class FeedbackEntry:
    """Single feedback entry."""
    feedback_id: str
    prompt: str
    response: str
    feedback_type: FeedbackType
    rating: Optional[float] = None  # 1-5 or 1-10
    preferred_response: Optional[str] = None  # For comparison
    correction: Optional[str] = None  # For correction
    reason: str = ""
    source: FeedbackSource = FeedbackSource.HUMAN
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PreferencePair:
    """Pair of responses with preference."""
    pair_id: str
    prompt: str
    chosen: str
    rejected: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeedbackCollector:
    """Collect and manage feedback."""

    def __init__(self):
        self._entries: List[FeedbackEntry] = []
        self._ratings: Dict[str, List[float]] = {}  # response_id -> ratings

    def add_rating(self, prompt: str, response: str, rating: float, reason: str = "") -> FeedbackEntry:
        entry = FeedbackEntry(
            feedback_id=str(uuid.uuid4())[:12],
            prompt=prompt,
            response=response,
            feedback_type=FeedbackType.RATING,
            rating=rating,
            reason=reason,
        )
        self._entries.append(entry)
        self._ratings.setdefault(response, []).append(rating)
        return entry

    def add_comparison(self, prompt: str, response_a: str, response_b: str, preferred: str, reason: str = "") -> PreferencePair:
        chosen = response_a if preferred == "a" else response_b
        rejected = response_b if preferred == "a" else response_a
        pair = PreferencePair(
            pair_id=str(uuid.uuid4())[:12],
            prompt=prompt,
            chosen=chosen,
            rejected=rejected,
            reason=reason,
        )
        self._entries.append(FeedbackEntry(
            feedback_id=pair.pair_id,
            prompt=prompt,
            response=chosen,
            feedback_type=FeedbackType.COMPARISON,
            preferred_response=chosen,
            reason=reason,
        ))
        return pair

    def add_correction(self, prompt: str, response: str, correction: str, reason: str = "") -> FeedbackEntry:
        entry = FeedbackEntry(
            feedback_id=str(uuid.uuid4())[:12],
            prompt=prompt,
            response=response,
            feedback_type=FeedbackType.CORRECTION,
            correction=correction,
            reason=reason,
        )
        self._entries.append(entry)
        return entry

    def get_average_rating(self, response: str) -> float:
        ratings = self._ratings.get(response, [])
        return sum(ratings) / max(len(ratings), 1)

    def get_stats(self) -> Dict[str, Any]:
        by_type = {}
        for e in self._entries:
            by_type[e.feedback_type.name] = by_type.get(e.feedback_type.name, 0) + 1
        return {
            "total_feedback": len(self._entries),
            "by_type": by_type,
            "rated_responses": len(self._ratings),
        }


class RewardModel:
    """Learn reward scores from feedback."""

    def __init__(self):
        self._weights: Dict[str, float] = {}  # feature -> weight
        self._response_scores: Dict[str, float] = {}

    def train(self, pairs: List[PreferencePair], learning_rate: float = 0.01) -> None:
        for pair in pairs:
            # Simple: chosen gets higher score, rejected lower
            chosen_features = self._extract_features(pair.chosen)
            rejected_features = self._extract_features(pair.rejected)
            # Update weights
            for feat in set(chosen_features.keys()) | set(rejected_features.keys()):
                diff = chosen_features.get(feat, 0) - rejected_features.get(feat, 0)
                self._weights[feat] = self._weights.get(feat, 0.0) + learning_rate * diff * pair.confidence

    def _extract_features(self, text: str) -> Dict[str, float]:
        features = {
            "length": min(1.0, len(text) / 500),
            "has_code": 1.0 if any(k in text for k in ["def ", "class ", "function", "{"]) else 0.0,
            "has_reasoning": 1.0 if any(k in text.lower() for k in ["because", "therefore", "reason"]) else 0.0,
            "has_examples": 1.0 if "example" in text.lower() else 0.0,
            "completeness": min(1.0, len(text.split(".")) / 5),
        }
        return features

    def score(self, text: str) -> float:
        features = self._extract_features(text)
        total = 0.0
        for feat, val in features.items():
            weight = self._weights.get(feat, 0.0)
            total += weight * val
        # Add bias
        score = 0.5 + total * 0.1
        return max(0.0, min(1.0, score))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "weights": self._weights,
            "num_weights": len(self._weights),
        }


class PreferenceDataset:
    """Manage preference pairs for training."""

    def __init__(self):
        self._pairs: List[PreferencePair] = []

    def add(self, pair: PreferencePair) -> None:
        self._pairs.append(pair)

    def add_from_feedback(self, collector: FeedbackCollector) -> int:
        count = 0
        for entry in collector._entries:
            if entry.feedback_type == FeedbackType.COMPARISON and entry.preferred_response:
                pair = PreferencePair(
                    pair_id=str(uuid.uuid4())[:12],
                    prompt=entry.prompt,
                    chosen=entry.preferred_response,
                    rejected=entry.response if entry.response != entry.preferred_response else "",
                )
                self._pairs.append(pair)
                count += 1
        return count

    def get_batch(self, n: int = 32) -> List[PreferencePair]:
        import random
        if len(self._pairs) <= n:
            return self._pairs
        return random.sample(self._pairs, n)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_pairs": len(self._pairs),
        }


class RLHFLoop:
    """Training loop for RLHF."""

    def __init__(self, reward_model: RewardModel, learning_rate: float = 0.01, epochs: int = 10):
        self.reward_model = reward_model
        self.lr = learning_rate
        self.epochs = epochs
        self._history: List[Dict[str, Any]] = []

    def train(self, dataset: PreferenceDataset, policy_fn: Optional[Callable[[str], str]] = None) -> Dict[str, Any]:
        for epoch in range(self.epochs):
            batch = dataset.get_batch(32)
            if not batch:
                break
            self.reward_model.train(batch, self.lr)
            avg_score = sum(self.reward_model.score(p.chosen) for p in batch) / len(batch)
            self._history.append({
                "epoch": epoch,
                "avg_reward": avg_score,
                "weights": dict(self.reward_model._weights),
            })
        return {
            "epochs": len(self._history),
            "final_avg_reward": self._history[-1]["avg_reward"] if self._history else 0,
        }

    def get_history(self) -> List[Dict[str, Any]]:
        return self._history


class FeedbackEngine:
    """End-to-end RLHF pipeline."""

    def __init__(self):
        self.collector = FeedbackCollector()
        self.reward_model = RewardModel()
        self.dataset = PreferenceDataset()
        self.trainer = RLHFLoop(self.reward_model)

    def collect_rating(self, prompt: str, response: str, rating: float, reason: str = "") -> FeedbackEntry:
        return self.collector.add_rating(prompt, response, rating, reason)

    def collect_comparison(self, prompt: str, response_a: str, response_b: str, preferred: str, reason: str = "") -> PreferencePair:
        return self.collector.add_comparison(prompt, response_a, response_b, preferred, reason)

    def collect_correction(self, prompt: str, response: str, correction: str, reason: str = "") -> FeedbackEntry:
        return self.collector.add_correction(prompt, response, correction, reason)

    def build_dataset(self) -> int:
        return self.dataset.add_from_feedback(self.collector)

    def train(self) -> Dict[str, Any]:
        self.build_dataset()
        return self.trainer.train(self.dataset)

    def score_response(self, text: str) -> float:
        return self.reward_model.score(text)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "feedback": self.collector.get_stats(),
            "dataset": self.dataset.get_stats(),
            "reward_model": self.reward_model.get_stats(),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.get_stats(),
                "history": self.trainer.get_history(),
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("FEEDBACK LOOP (RLHF) DEMO")
    print("=" * 70)

    engine = FeedbackEngine()

    # 1. Collect ratings
    print("\n[1] Collect Ratings")
    engine.collect_rating("What is AI?", "AI is artificial intelligence", 4.5, "Clear and concise")
    engine.collect_rating("What is AI?", "AI stands for Artificial Intelligence, which is a field of computer science", 3.5, "Too verbose")
    engine.collect_rating("What is Python?", "Python is a programming language", 5.0, "Perfect")
    print(f"  {engine.collector.get_stats()}")

    # 2. Collect comparisons
    print("\n[2] Collect Comparisons")
    pair1 = engine.collect_comparison(
        "Explain Python",
        "Python is easy to learn",
        "Python is a high-level programming language that is easy to learn and widely used",
        "b",
        "More detailed"
    )
    pair2 = engine.collect_comparison(
        "Explain Python",
        "Python is a programming language",
        "Python is a versatile language with simple syntax",
        "b",
        "Better explanation"
    )
    print(f"  Pairs collected: {engine.dataset.get_stats()}")

    # 3. Collect corrections
    print("\n[3] Collect Corrections")
    engine.collect_correction(
        "What is 2+2?",
        "5",
        "4",
        "Mathematical error"
    )
    print(f"  Total feedback: {len(engine.collector._entries)}")

    # 4. Train reward model
    print("\n[4] Train Reward Model")
    engine.build_dataset()
    result = engine.train()
    print(f"  Training epochs: {result['epochs']}")
    print(f"  Final avg reward: {result['final_avg_reward']:.3f}")

    # 5. Score responses
    print("\n[5] Score Responses")
    responses = [
        "Python is a programming language",
        "Python is a high-level, interpreted programming language with simple syntax, widely used in data science, web development, and automation.",
        "def hello(): return 'world'",
    ]
    for r in responses:
        score = engine.score_response(r)
        print(f"  Score {score:.3f}: {r[:50]}...")

    # 6. Reward model weights
    print(f"\n[6] Reward Model Weights")
    print(f"  {engine.reward_model.get_stats()}")

    # 7. Export
    print("\n[7] Export")
    engine.export("/tmp/rlhf.json")
    print("  Exported to /tmp/rlhf.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
