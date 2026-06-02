#!/usr/bin/env python3
"""
MAGNATRIX-OS — Meta-Learning / Few-Shot Adaptation Engine
ai/llm_meta_learning_native.py

Features:
- Few-shot example manager (store, retrieve, rank examples)
- Task similarity scoring (cosine similarity, keyword overlap)
- Prompt template adaptation (adapt templates based on task type)
- Learning curve tracking (performance over examples)
- Meta-parameter optimization (learning rate, temperature, top-k adaptation)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("meta_learning")


class ExampleType(enum.Enum):
    FEW_SHOT = "few_shot"
    ZERO_SHOT = "zero_shot"
    ONE_SHOT = "one_shot"
    FEW_SHOT_CHAIN = "few_shot_chain"


@dataclass
class Example:
    id: str
    task: str
    input_text: str
    output_text: str
    task_type: str
    difficulty: float = 0.5
    quality_score: float = 1.0


@dataclass
class TaskProfile:
    task_type: str
    keywords: List[str]
    avg_input_length: float
    avg_output_length: float
    example_count: int
    success_rate: float


@dataclass
class AdaptationResult:
    task_type: str
    selected_examples: List[Example]
    template: str
    meta_params: Dict[str, Any]
    estimated_performance: float


class ExampleStore:
    """Store and retrieve few-shot examples."""

    def __init__(self, max_examples: int = 1000):
        self._examples: List[Example] = []
        self._max_examples = max_examples
        self._by_task: Dict[str, List[Example]] = defaultdict(list)

    def add(self, example: Example) -> None:
        if len(self._examples) >= self._max_examples:
            self._examples.pop(0)
        self._examples.append(example)
        self._by_task[example.task_type].append(example)

    def get_by_task(self, task_type: str, n: int = 5) -> List[Example]:
        examples = self._by_task.get(task_type, [])
        return sorted(examples, key=lambda e: e.quality_score, reverse=True)[:n]

    def get_all(self, n: int = 10) -> List[Example]:
        return sorted(self._examples, key=lambda e: e.quality_score, reverse=True)[:n]

    def get_task_types(self) -> List[str]:
        return list(self._by_task.keys())

    def size(self) -> int:
        return len(self._examples)


class TaskSimilarity:
    """Score task similarity for example selection."""

    @staticmethod
    def keyword_overlap(task1: str, task2: str) -> float:
        words1 = set(task1.lower().split())
        words2 = set(task2.lower().split())
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        return dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0

    @staticmethod
    def simple_embedding(text: str) -> List[float]:
        """Create a simple word-frequency embedding."""
        words = text.lower().split()
        vocab = sorted(set(words))
        return [words.count(w) for w in vocab[:50]] + [0.0] * (50 - len(vocab))

    def score(self, task_a: str, task_b: str) -> float:
        kw_score = self.keyword_overlap(task_a, task_b)
        emb_a = self.simple_embedding(task_a)
        emb_b = self.simple_embedding(task_b)
        cos_score = self.cosine_similarity(emb_a, emb_b)
        return 0.5 * kw_score + 0.5 * cos_score


class TemplateLibrary:
    """Adaptable prompt templates."""

    TEMPLATES = {
        "classification": "Classify the following text into one of the categories.\n\nExamples:\n{examples}\n\nText: {input}\nCategory:",
        "generation": "Generate a response based on the following examples.\n\nExamples:\n{examples}\n\nInput: {input}\nOutput:",
        "qa": "Answer the question based on the examples.\n\nExamples:\n{examples}\n\nQuestion: {input}\nAnswer:",
        "summarization": "Summarize the following text.\n\nExamples:\n{examples}\n\nText: {input}\nSummary:",
        "translation": "Translate the following text.\n\nExamples:\n{examples}\n\nText: {input}\nTranslation:",
    }

    def get_template(self, task_type: str) -> str:
        return self.TEMPLATES.get(task_type, self.TEMPLATES["generation"])

    def format_examples(self, examples: List[Example]) -> str:
        lines = []
        for ex in examples:
            lines.append(f"Input: {ex.input_text}\nOutput: {ex.output_text}")
        return "\n\n".join(lines)

    def adapt(self, task_type: str, examples: List[Example], input_text: str) -> str:
        template = self.get_template(task_type)
        formatted = self.format_examples(examples)
        return template.replace("{examples}", formatted).replace("{input}", input_text)


class MetaParameterOptimizer:
    """Optimize meta-parameters based on task and examples."""

    def optimize(self, task_type: str, example_count: int, task_complexity: float) -> Dict[str, Any]:
        params = {
            "temperature": 0.7,
            "top_k": 50,
            "max_tokens": 256,
            "repetition_penalty": 1.0,
        }
        if task_type == "classification":
            params["temperature"] = 0.3
            params["top_k"] = 10
        elif task_type == "generation":
            params["temperature"] = 0.8
            params["max_tokens"] = 512
        elif task_type == "qa":
            params["temperature"] = 0.5
            params["max_tokens"] = 128

        # Adjust by complexity
        if task_complexity > 0.7:
            params["temperature"] = min(params["temperature"] + 0.1, 1.0)
            params["max_tokens"] = int(params["max_tokens"] * 1.5)

        # Adjust by example count (more examples = lower temperature for stability)
        if example_count > 5:
            params["temperature"] = max(params["temperature"] - 0.1, 0.1)

        return params


class LearningCurveTracker:
    """Track performance improvement over examples."""

    def __init__(self):
        self._points: List[Tuple[int, float]] = []

    def record(self, example_count: int, performance: float) -> None:
        self._points.append((example_count, performance))

    def estimate_saturation(self) -> Optional[int]:
        """Estimate when adding more examples stops helping."""
        if len(self._points) < 3:
            return None
        # Find where improvement drops below 2%
        for i in range(1, len(self._points)):
            prev_perf = self._points[i - 1][1]
            curr_perf = self._points[i][1]
            if curr_perf - prev_perf < 0.02:
                return self._points[i][0]
        return None

    def get_curve(self) -> List[Tuple[int, float]]:
        return list(self._points)


class MetaLearningEngine:
    """Unified meta-learning engine."""

    def __init__(self):
        self.store = ExampleStore()
        self.similarity = TaskSimilarity()
        self.templates = TemplateLibrary()
        self.optimizer = MetaParameterOptimizer()
        self.curve_tracker = LearningCurveTracker()
        self._task_profiles: Dict[str, TaskProfile] = {}

    def add_example(self, example: Example) -> None:
        self.store.add(example)
        self._update_profile(example.task_type)

    def adapt(self, task: str, task_type: str, input_text: str, n_examples: int = 3) -> AdaptationResult:
        """Adapt to a new task using few-shot examples."""
        # Find similar examples
        candidates = self.store.get_by_task(task_type, n=20)
        if not candidates:
            candidates = self.store.get_all(n=20)

        scored = []
        for ex in candidates:
            score = self.similarity.score(task, ex.task)
            scored.append((score, ex))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [ex for _, ex in scored[:n_examples]]

        # Get template
        template = self.templates.adapt(task_type, selected, input_text)

        # Optimize meta-parameters
        complexity = self._estimate_complexity(task)
        params = self.optimizer.optimize(task_type, len(selected), complexity)

        # Estimate performance
        perf = self._estimate_performance(task_type, len(selected))

        return AdaptationResult(
            task_type=task_type,
            selected_examples=selected,
            template=template,
            meta_params=params,
            estimated_performance=perf,
        )

    def _update_profile(self, task_type: str) -> None:
        examples = self.store._by_task.get(task_type, [])
        if not examples:
            return
        avg_in = sum(len(e.input_text) for e in examples) / len(examples)
        avg_out = sum(len(e.output_text) for e in examples) / len(examples)
        self._task_profiles[task_type] = TaskProfile(
            task_type=task_type,
            keywords=list(set(w.lower() for e in examples for w in e.task.split())),
            avg_input_length=avg_in,
            avg_output_length=avg_out,
            example_count=len(examples),
            success_rate=0.85,  # simulated
        )

    def _estimate_complexity(self, task: str) -> float:
        words = len(task.split())
        complexity = min(words / 50, 1.0)
        if any(w in task.lower() for w in ["explain", "analyze", "compare", "evaluate", "synthesize"]):
            complexity += 0.2
        return min(complexity, 1.0)

    def _estimate_performance(self, task_type: str, n_examples: int) -> float:
        base = 0.6
        per_example = 0.05
        return min(base + n_examples * per_example, 0.95)

    def get_task_profile(self, task_type: str) -> Optional[TaskProfile]:
        return self._task_profiles.get(task_type)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_examples": self.store.size(),
            "task_types": self.store.get_task_types(),
            "task_profiles": {k: {"example_count": v.example_count, "success_rate": v.success_rate} for k, v in self._task_profiles.items()},
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Meta-Learning / Few-Shot Adaptation Engine")
    print("ai/llm_meta_learning_native.py")
    print("=" * 60)

    engine = MetaLearningEngine()

    # Add examples
    examples = [
        Example("E1", "Classify sentiment", "I love this product!", "positive", "classification", difficulty=0.3),
        Example("E2", "Classify sentiment", "This is terrible.", "negative", "classification", difficulty=0.3),
        Example("E3", "Classify sentiment", "It is okay.", "neutral", "classification", difficulty=0.4),
        Example("E4", "Translate to French", "Hello world", "Bonjour le monde", "translation", difficulty=0.2),
        Example("E5", "Translate to French", "Good morning", "Bonjour", "translation", difficulty=0.2),
        Example("E6", "Generate summary", "The quick brown fox jumps over the lazy dog. The fox was very fast and the dog was sleeping.", "A fox jumps over a sleeping dog.", "summarization", difficulty=0.5),
        Example("E7", "Answer question", "What is the capital of France?", "Paris", "qa", difficulty=0.2),
        Example("E8", "Answer question", "What is 2+2?", "4", "qa", difficulty=0.1),
    ]
    for ex in examples:
        engine.add_example(ex)

    # 1. Few-shot adaptation for classification
    print("")
    print("[1] Few-Shot Adaptation - Classification")
    result = engine.adapt("Classify sentiment", "classification", "I am very happy today!", n_examples=3)
    print(f"  Task: {result.task_type}")
    print(f"  Selected examples: {len(result.selected_examples)}")
    for ex in result.selected_examples:
        print(f"    {ex.id}: {ex.input_text} -> {ex.output_text}")
    print(f"  Meta params: {result.meta_params}")
    print(f"  Estimated performance: {result.estimated_performance:.2f}")

    # 2. Template adaptation
    print("")
    print("[2] Template Adaptation")
    result2 = engine.adapt("Translate to French", "translation", "How are you?", n_examples=2)
    print(f"  Template preview: {result2.template[:200]}...")

    # 3. Meta-parameter optimization
    print("")
    print("[3] Meta-Parameter Optimization")
    for task_type in ["classification", "generation", "qa"]:
        params = engine.optimizer.optimize(task_type, example_count=5, task_complexity=0.5)
        print(f"  {task_type}: temp={params['temperature']}, top_k={params['top_k']}, max_tokens={params['max_tokens']}")

    # 4. Task similarity
    print("")
    print("[4] Task Similarity")
    score = engine.similarity.score("Classify sentiment", "Analyze sentiment of text")
    print(f"  'Classify sentiment' vs 'Analyze sentiment': {score:.3f}")
    score2 = engine.similarity.score("Classify sentiment", "Translate to French")
    print(f"  'Classify sentiment' vs 'Translate to French': {score2:.3f}")

    # 5. Learning curve
    print("")
    print("[5] Learning Curve Tracking")
    for n in range(1, 8):
        perf = engine._estimate_performance("classification", n)
        engine.curve_tracker.record(n, perf)
    curve = engine.curve_tracker.get_curve()
    for point in curve:
        print(f"  Examples: {point[0]}, Performance: {point[1]:.2f}")
    saturation = engine.curve_tracker.estimate_saturation()
    print(f"  Saturation point: {saturation}")

    # 6. Stats
    print("")
    print("[6] Engine Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("")
    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
