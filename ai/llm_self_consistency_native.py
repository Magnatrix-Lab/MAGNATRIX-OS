#!/usr/bin/env python3
"""
MAGNATRIX-OS — Self-Consistency Engine
ai/llm_self_consistency_native.py

Features:
- Multiple path generation (generate N reasoning paths for same question)
- Answer extraction and clustering (group similar answers)
- Confidence scoring by consensus (vote aggregation)
- Path divergency detection (identify outliers)
- Consensus-based final answer selection

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("self_consistency")


class PathStatus(enum.Enum):
    VALID = "valid"
    DIVERGENT = "divergent"
    OUTLIER = "outlier"


@dataclass
class ReasoningPath:
    id: int
    steps: List[str]
    answer: str
    confidence: float
    status: PathStatus = PathStatus.VALID


@dataclass
class ConsensusResult:
    answer: str
    confidence: float
    vote_count: int
    total_paths: int
    all_answers: Dict[str, int]


class SelfConsistencyEngine:
    """Generate multiple reasoning paths and select consensus answer."""

    def __init__(self, paths_per_question: int = 5, confidence_threshold: float = 0.6):
        self.paths_per_question = paths_per_question
        self.confidence_threshold = confidence_threshold
        self._history: List[Dict[str, Any]] = []

    def generate_paths(self, question: str, generator: Callable[[str], Tuple[List[str], str]]) -> List[ReasoningPath]:
        """Generate multiple reasoning paths using the provided generator."""
        paths = []
        for i in range(self.paths_per_question):
            steps, answer = generator(question)
            path = ReasoningPath(id=i, steps=steps, answer=answer, confidence=self._score_path(steps))
            paths.append(path)
        return paths

    def _score_path(self, steps: List[str]) -> float:
        """Score a reasoning path based on coherence and length."""
        if not steps:
            return 0.0
        # Simple heuristic: longer paths with logical connectors score higher
        logical_connectors = ["because", "therefore", "since", "thus", "hence", "so", "as"]
        connector_count = sum(1 for step in steps for conn in logical_connectors if conn in step.lower())
        base = 0.5 + min(len(steps) * 0.05, 0.3)
        bonus = min(connector_count * 0.05, 0.2)
        return min(base + bonus, 1.0)

    def cluster_answers(self, paths: List[ReasoningPath]) -> Dict[str, List[ReasoningPath]]:
        """Cluster paths by their answers."""
        clusters: Dict[str, List[ReasoningPath]] = defaultdict(list)
        for path in paths:
            clusters[path.answer].append(path)
        return dict(clusters)

    def detect_outliers(self, paths: List[ReasoningPath]) -> List[ReasoningPath]:
        """Mark paths that are statistical outliers."""
        clusters = self.cluster_answers(paths)
        if not clusters:
            return paths
        max_cluster_size = max(len(v) for v in clusters.values())
        for path in paths:
            cluster_size = len(clusters.get(path.answer, []))
            if cluster_size == 1 and max_cluster_size > 2:
                path.status = PathStatus.OUTLIER
            elif cluster_size < max_cluster_size * 0.3:
                path.status = PathStatus.DIVERGENT
        return paths

    def vote(self, paths: List[ReasoningPath]) -> ConsensusResult:
        """Aggregate votes and select consensus answer."""
        # Exclude outliers from voting
        valid_paths = [p for p in paths if p.status != PathStatus.OUTLIER]
        if not valid_paths:
            valid_paths = paths
        answers = [p.answer for p in valid_paths]
        vote_counts = Counter(answers)
        if not vote_counts:
            return ConsensusResult(answer="", confidence=0.0, vote_count=0, total_paths=len(paths), all_answers={})
        best_answer, best_count = vote_counts.most_common(1)[0]
        confidence = best_count / len(valid_paths)
        return ConsensusResult(
            answer=best_answer,
            confidence=confidence,
            vote_count=best_count,
            total_paths=len(paths),
            all_answers=dict(vote_counts),
        )

    def solve(self, question: str, generator: Callable[[str], Tuple[List[str], str]]) -> Dict[str, Any]:
        """End-to-end: generate, cluster, detect outliers, vote."""
        paths = self.generate_paths(question, generator)
        clusters = self.cluster_answers(paths)
        paths = self.detect_outliers(paths)
        consensus = self.vote(paths)

        result = {
            "question": question,
            "paths_generated": len(paths),
            "clusters": {k: len(v) for k, v in clusters.items()},
            "consensus": {
                "answer": consensus.answer,
                "confidence": consensus.confidence,
                "vote_count": consensus.vote_count,
            },
            "divergent_paths": sum(1 for p in paths if p.status == PathStatus.DIVERGENT),
            "outlier_paths": sum(1 for p in paths if p.status == PathStatus.OUTLIER),
        }
        self._history.append(result)
        return result

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Self-Consistency Engine")
    print("ai/llm_self_consistency_native.py")
    print("=" * 60)

    engine = SelfConsistencyEngine(paths_per_question=7, confidence_threshold=0.6)

    # 1. Math problem with consensus
    print("")
    print("[1] Math Problem (consensus expected)")
    def math_generator(question: str) -> Tuple[List[str], str]:
        # Simulate a math problem: "What is 15 + 27?"
        # Most paths should agree on 42
        if random.random() < 0.8:
            return ["Break into 15 + 20 = 35", "Then 35 + 7 = 42"], "42"
        else:
            return ["15 + 27 = 30 + 12 = 42"], "42"

    result = engine.solve("What is 15 + 27?", math_generator)
    print(f"  Question: {result['question']}")
    print(f"  Consensus: {result['consensus']['answer']} (confidence={result['consensus']['confidence']:.2f})")
    print(f"  Clusters: {result['clusters']}")

    # 2. Problem with divergent paths
    print("")
    print("[2] Problem with Divergent Paths")
    def divergent_generator(question: str) -> Tuple[List[str], str]:
        r = random.random()
        if r < 0.5:
            return ["Analyze option A", "A is correct"], "A"
        elif r < 0.3:
            return ["Analyze option B", "B is correct"], "B"
        else:
            return ["Analyze option C", "C is correct"], "C"

    result2 = engine.solve("Which is the best option?", divergent_generator)
    print(f"  Consensus: {result2['consensus']['answer']} (confidence={result2['consensus']['confidence']:.2f})")
    print(f"  Clusters: {result2['clusters']}")
    print(f"  Divergent paths: {result2['divergent_paths']}, Outliers: {result2['outlier_paths']}")

    # 3. Outlier detection
    print("")
    print("[3] Outlier Detection")
    def outlier_generator(question: str) -> Tuple[List[str], str]:
        r = random.random()
        if r < 0.7:
            return ["Step 1", "Step 2"], "correct"
        elif r < 0.9:
            return ["Alt step 1", "Alt step 2"], "alternative"
        else:
            return ["Wrong step"], "wrong"

    result3 = engine.solve("Find the answer.", outlier_generator)
    print(f"  Consensus: {result3['consensus']['answer']} (confidence={result3['consensus']['confidence']:.2f})")
    print(f"  Outliers detected: {result3['outlier_paths']}")

    # 4. Path confidence scoring
    print("")
    print("[4] Path Confidence Scoring")
    paths = engine.generate_paths("Test", lambda q: (["Because X, therefore Y"], "Y"))
    for p in paths[:3]:
        print(f"  Path {p.id}: confidence={p.confidence:.2f}, steps={len(p.steps)}")

    print("")
    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
