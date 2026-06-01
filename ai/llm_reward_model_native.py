"""Reward Model & Feedback Loop — RLHF-style reward scoring, preference learning, human feedback.

Modul ini menyediakan:
- RewardModel: score responses with multiple dimensions
- PreferenceLearner: learn from pairwise comparisons
- FeedbackCollector: gather human feedback efficiently
- RewardTrainer: train reward model from feedback data
- RLHFLoop: end-to-end RLHF pipeline simulation
"""

from __future__ import annotations

import json
import time
import uuid
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class RewardDimension(Enum):
    HELPFULNESS = "helpfulness"
    HARMLESSNESS = "harmlessness"
    HONESTY = "honesty"
    CLARITY = "clarity"
    CONCISENESS = "conciseness"
    CREATIVITY = "creativity"
    FACTUALITY = "factuality"
    INSTRUCTION_FOLLOWING = "instruction_following"


class FeedbackType(Enum):
    RATING = auto()       # 1-5 scale
    COMPARISON = auto()   # A vs B preference
    BINARY = auto()       # thumbs up/down
    CORRECTION = auto()   # provide correct answer


@dataclass
class RewardScore:
    """Multi-dimensional reward score."""
    response_id: str
    overall: float
    dimensions: Dict[str, float]
    confidence: float = 1.0
    model_version: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class PreferencePair:
    """Pairwise preference for training."""
    pair_id: str
    prompt: str
    chosen: str
    rejected: str
    preference_strength: float = 1.0
    source: str = "human"  # human or synthetic
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackRecord:
    """Single feedback record."""
    feedback_id: str
    response_id: str
    feedback_type: FeedbackType
    value: Any
    user_id: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RewardModel:
    """Score responses across multiple dimensions."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            "helpfulness": 0.25,
            "harmlessness": 0.20,
            "honesty": 0.15,
            "clarity": 0.15,
            "conciseness": 0.10,
            "factuality": 0.15
        }
        self._history: List[RewardScore] = []

    def score(self, response_id: str, response_text: str, prompt: str = "",
              scoring_fn: Optional[Callable[[str, str], Dict[str, float]]] = None) -> RewardScore:
        scoring_fn = scoring_fn or self._default_scoring
        dims = scoring_fn(response_text, prompt)
        overall = sum(dims.get(k, 0.5) * self.weights.get(k, 0.1) for k in set(dims) | set(self.weights))
        overall = max(0.0, min(1.0, overall))
        score = RewardScore(
            response_id=response_id,
            overall=round(overall, 4),
            dimensions={k: round(v, 4) for k, v in dims.items()}
        )
        self._history.append(score)
        return score

    def _default_scoring(self, response: str, prompt: str) -> Dict[str, float]:
        # Simulated scoring based on heuristics
        scores = {}
        # Helpfulness: length, contains relevant keywords
        scores["helpfulness"] = min(1.0, len(response) / 500)
        # Harmlessness: no harmful patterns (simplified)
        harmful = any(w in response.lower() for w in ["kill", "harm", "attack", "destroy"])
        scores["harmlessness"] = 0.0 if harmful else 1.0
        # Honesty: contains uncertainty markers
        honest = any(w in response.lower() for w in ["i think", "maybe", "possibly", "not sure"])
        scores["honesty"] = 0.7 if honest else 0.5
        # Clarity: sentence structure, punctuation
        sentences = response.split(". ")
        scores["clarity"] = min(1.0, len(sentences) / 10)
        # Conciseness: ratio of content to length
        scores["conciseness"] = min(1.0, 200 / max(len(response), 1))
        # Factuality: contains factual markers
        factual = any(w in response.lower() for w in ["according to", "study", "research", "data"])
        scores["factuality"] = 0.8 if factual else 0.5
        return scores

    def compare(self, response_a: str, response_b: str, prompt: str = "") -> Tuple[str, float]:
        """Compare two responses, return (winner_id, margin)."""
        score_a = self.score("a", response_a, prompt)
        score_b = self.score("b", response_b, prompt)
        if score_a.overall > score_b.overall:
            return "a", score_a.overall - score_b.overall
        return "b", score_b.overall - score_a.overall

    def get_history(self) -> List[RewardScore]:
        return self._history


class PreferenceLearner:
    """Learn reward model from pairwise preferences."""

    def __init__(self, learning_rate: float = 0.01):
        self.lr = learning_rate
        self._pairs: List[PreferencePair] = []
        self._weights: Dict[str, float] = {}
        self._epoch_losses: List[float] = []

    def add_preference(self, pair: PreferencePair) -> None:
        self._pairs.append(pair)

    def train(self, epochs: int = 10) -> Dict[str, float]:
        """Simulated preference learning."""
        for epoch in range(epochs):
            total_loss = 0.0
            for pair in self._pairs:
                # Simulated loss: logistic loss on preference
                margin = pair.preference_strength
                loss = max(0, 1.0 - margin)
                total_loss += loss
                # Update weights (simplified)
                for dim in ["helpfulness", "harmlessness", "clarity"]:
                    self._weights[dim] = self._weights.get(dim, 0.5) + self.lr * margin * random.uniform(-0.1, 0.1)
            avg_loss = total_loss / max(len(self._pairs), 1)
            self._epoch_losses.append(avg_loss)
        return {k: round(v, 4) for k, v in self._weights.items()}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "pairs": len(self._pairs),
            "epochs_trained": len(self._epoch_losses),
            "final_loss": round(self._epoch_losses[-1], 4) if self._epoch_losses else None,
            "weights": self._weights
        }


class FeedbackCollector:
    """Gather human feedback efficiently."""

    def __init__(self, target_samples: int = 1000):
        self.target = target_samples
        self._records: List[FeedbackRecord] = []
        self._by_type: Dict[FeedbackType, int] = {t: 0 for t in FeedbackType}
        self._by_response: Dict[str, List[FeedbackRecord]] = {}

    def collect(self, response_id: str, feedback_type: FeedbackType, value: Any,
                user_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> FeedbackRecord:
        record = FeedbackRecord(
            feedback_id=str(uuid.uuid4())[:12],
            response_id=response_id,
            feedback_type=feedback_type,
            value=value,
            user_id=user_id,
            metadata=metadata or {}
        )
        self._records.append(record)
        self._by_type[feedback_type] += 1
        self._by_response.setdefault(response_id, []).append(record)
        return record

    def get_preferences(self) -> List[PreferencePair]:
        """Extract preference pairs from comparison feedback."""
        pairs = []
        for response_id, records in self._by_response.items():
            comparisons = [r for r in records if r.feedback_type == FeedbackType.COMPARISON]
            for comp in comparisons:
                if isinstance(comp.value, dict) and "chosen" in comp.value and "rejected" in comp.value:
                    pairs.append(PreferencePair(
                        pair_id=str(uuid.uuid4())[:12],
                        prompt=comp.value.get("prompt", ""),
                        chosen=comp.value["chosen"],
                        rejected=comp.value["rejected"],
                        preference_strength=comp.value.get("strength", 1.0)
                    ))
        return pairs

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": len(self._records),
            "by_type": {k.name: v for k, v in self._by_type.items()},
            "target": self.target,
            "progress": round(len(self._records) / max(self.target, 1), 3),
            "responses_with_feedback": len(self._by_response)
        }


class RewardTrainer:
    """Train reward model from collected feedback."""

    def __init__(self, reward_model: RewardModel):
        self.model = reward_model
        self._trained = False
        self._metrics: Dict[str, Any] = {}

    def train_from_feedback(self, collector: FeedbackCollector, epochs: int = 5) -> Dict[str, Any]:
        preferences = collector.get_preferences()
        learner = PreferenceLearner()
        for pair in preferences:
            learner.add_preference(pair)
        weights = learner.train(epochs)
        self.model.weights.update(weights)
        self._trained = True
        self._metrics = {
            "preferences_used": len(preferences),
            "epochs": epochs,
            "learned_weights": weights
        }
        return self._metrics

    def evaluate(self, test_responses: List[Tuple[str, str, str]]) -> Dict[str, Any]:
        """Evaluate on test set."""
        correct = 0
        for prompt, chosen, rejected in test_responses:
            winner, margin = self.model.compare(chosen, rejected, prompt)
            if winner == "a":  # chosen is "a"
                correct += 1
        accuracy = correct / max(len(test_responses), 1)
        return {"accuracy": round(accuracy, 4), "total": len(test_responses)}


class RLHFLoop:
    """End-to-end RLHF pipeline simulation."""

    def __init__(self, target_feedback: int = 100):
        self.target = target_feedback
        self.reward_model = RewardModel()
        self.collector = FeedbackCollector(target_feedback)
        self.trainer = RewardTrainer(self.reward_model)
        self._loop_count = 0
        self._history: List[Dict[str, Any]] = []

    def collect_and_train(self, synthetic_pairs: int = 50) -> Dict[str, Any]:
        # Generate synthetic feedback
        for i in range(synthetic_pairs):
            prompt = f"Question {i}"
            chosen = f"Good answer {i} with helpful details."
            rejected = f"Bad answer {i}"
            self.collector.collect(
                f"resp-{i}",
                FeedbackType.COMPARISON,
                {"prompt": prompt, "chosen": chosen, "rejected": rejected, "strength": random.uniform(0.5, 1.0)}
            )
        # Train
        metrics = self.trainer.train_from_feedback(self.collector, epochs=5)
        self._loop_count += 1
        record = {
            "loop": self._loop_count,
            "feedback_count": len(self.collector._records),
            "metrics": metrics
        }
        self._history.append(record)
        return record

    def score_response(self, response: str, prompt: str = "") -> RewardScore:
        return self.reward_model.score(str(uuid.uuid4())[:8], response, prompt)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "loops": self._loop_count,
            "feedback_collected": len(self.collector._records),
            "reward_history": len(self.reward_model._history),
            "weights": self.reward_model.weights
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.get_stats(),
                "history": self._history
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("REWARD MODEL & FEEDBACK LOOP DEMO")
    print("=" * 70)

    # 1. Reward Model
    print("\n[1] Reward Model Scoring")
    rm = RewardModel()
    responses = [
        ("r1", "I think the answer is probably 42. Maybe you should verify this."),
        ("r2", "The answer is 42. According to research in mathematics, this is the ultimate answer."),
        ("r3", "Kill all enemies. Attack immediately. Destroy everything."),
    ]
    for rid, resp in responses:
        score = rm.score(rid, resp)
        print(f"  {rid}: overall={score.overall:.3f} | dims={score.dimensions}")

    # 2. Comparison
    print("\n[2] Response Comparison")
    winner, margin = rm.compare("This is a clear, helpful answer.", "bad unclear wrong", "How does X work?")
    print(f"  Winner: {winner}, Margin: {margin:.3f}")

    # 3. Preference Learning
    print("\n[3] Preference Learning")
    pl = PreferenceLearner(learning_rate=0.05)
    for i in range(20):
        pl.add_preference(PreferencePair(
            pair_id=str(i),
            prompt=f"Q{i}",
            chosen=f"Good answer {i}",
            rejected=f"Bad answer {i}",
            preference_strength=random.uniform(0.7, 1.0)
        ))
    weights = pl.train(epochs=10)
    print(f"  Learned weights: {weights}")
    print(f"  Stats: {pl.get_stats()}")

    # 4. Feedback Collector
    print("\n[4] Feedback Collector")
    fc = FeedbackCollector(target_samples=100)
    for i in range(30):
        fc.collect(f"resp-{i}", FeedbackType.RATING, random.randint(1, 5))
    for i in range(15):
        fc.collect(f"resp-{i}", FeedbackType.COMPARISON, {
            "prompt": f"Q{i}", "chosen": f"A{i}", "rejected": f"B{i}", "strength": 0.8
        })
    for i in range(10):
        fc.collect(f"resp-{i}", FeedbackType.BINARY, random.choice([True, False]))
    print(f"  Stats: {fc.get_stats()}")
    print(f"  Preferences extracted: {len(fc.get_preferences())}")

    # 5. Reward Trainer
    print("\n[5] Reward Trainer")
    rt = RewardTrainer(RewardModel())
    metrics = rt.train_from_feedback(fc, epochs=5)
    print(f"  Training metrics: {metrics}")
    test_set = [(f"Q{i}", f"Good{i}", f"Bad{i}") for i in range(10)]
    eval_result = rt.evaluate(test_set)
    print(f"  Evaluation: {eval_result}")

    # 6. RLHF Loop
    print("\n[6] Full RLHF Loop")
    loop = RLHFLoop(target_feedback=50)
    for i in range(3):
        result = loop.collect_and_train(synthetic_pairs=20)
        print(f"  Loop {i+1}: feedback={result['feedback_count']}, prefs={result['metrics']['preferences_used']}")
    score = loop.score_response("This is a helpful, honest, and harmless response.")
    print(f"  Final score: {score.overall:.3f}")
    print(f"  Loop stats: {loop.get_stats()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
