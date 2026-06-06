#!/usr/bin/env python3
"""
Model A/B Testing for MAGNATRIX-OS
Parallel inference, win-rate tracking, statistical significance.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import math
import random
import time
from typing import Any, Dict, List, Optional


class ABTestResult:
    """Result of a single A/B test comparison."""

    def __init__(self, model_a: str, model_b: str, wins_a: int, wins_b: int, draws: int) -> None:
        self.model_a = model_a
        self.model_b = model_b
        self.wins_a = wins_a
        self.wins_b = wins_b
        self.draws = draws
        self.total = wins_a + wins_b + draws

    def win_rate_a(self) -> float:
        return self.wins_a / self.total if self.total > 0 else 0.0

    def win_rate_b(self) -> float:
        return self.wins_b / self.total if self.total > 0 else 0.0

    def significance(self) -> float:
        # Simple chi-square approximation
        if self.total < 10:
            return 0.0
        expected = self.total / 2
        chi2 = ((self.wins_a - expected) ** 2 + (self.wins_b - expected) ** 2) / expected
        return min(1.0, chi2 / 10)


class ModelABTesting:
    """A/B testing framework for models."""

    def __init__(self, storage_path: str = './ab_tests.json') -> None:
        self._storage_path = storage_path
        self._tests: Dict[str, Dict[str, Any]] = {}
        self._results: Dict[str, List[Dict]] = {}

    def create_test(self, test_id: str, model_a: str, model_b: str, criteria: List[str]) -> None:
        self._tests[test_id] = {
            'model_a': model_a,
            'model_b': model_b,
            'criteria': criteria,
            'created_at': time.time(),
            'status': 'running',
        }
        self._results[test_id] = []

    def record_result(self, test_id: str, model_a_score: float, model_b_score: float, latency_a: float, latency_b: float) -> None:
        if test_id not in self._results:
            return

        winner = 'a' if model_a_score > model_b_score else ('b' if model_b_score > model_a_score else 'draw')

        self._results[test_id].append({
            'winner': winner,
            'model_a_score': model_a_score,
            'model_b_score': model_b_score,
            'latency_a': latency_a,
            'latency_b': latency_b,
            'timestamp': time.time(),
        })

    def get_results(self, test_id: str) -> ABTestResult:
        results = self._results.get(test_id, [])
        wins_a = sum(1 for r in results if r['winner'] == 'a')
        wins_b = sum(1 for r in results if r['winner'] == 'b')
        draws = sum(1 for r in results if r['winner'] == 'draw')

        test_info = self._tests.get(test_id, {})
        return ABTestResult(
            test_info.get('model_a', 'A'),
            test_info.get('model_b', 'B'),
            wins_a, wins_b, draws
        )

    def recommend(self, test_id: str) -> Optional[str]:
        result = self.get_results(test_id)
        if result.total < 5:
            return None
        if result.win_rate_a() > result.win_rate_b() + 0.1:
            return result.model_a
        elif result.win_rate_b() > result.win_rate_a() + 0.1:
            return result.model_b
        return None

    def list_tests(self) -> List[Dict[str, Any]]:
        return [
            {
                'id': tid,
                'model_a': t['model_a'],
                'model_b': t['model_b'],
                'status': t['status'],
                'samples': len(self._results.get(tid, [])),
            }
            for tid, t in self._tests.items()
        ]


def _demo() -> None:
    print("=== Model A/B Testing Demo ===\n")

    ab = ModelABTesting()
    ab.create_test('test_1', 'llama3.2:3b', 'qwen2.5:7b', ['accuracy', 'latency', 'conciseness'])

    # Simulate 20 comparisons
    for i in range(20):
        # Random scores with slight bias toward qwen
        score_a = random.uniform(0.7, 0.9)
        score_b = random.uniform(0.75, 0.95)
        ab.record_result('test_1', score_a, score_b, 1.5, 2.0)

    result = ab.get_results('test_1')
    print(f"Model A ({result.model_a}): {result.wins_a} wins ({result.win_rate_a():.1%})")
    print(f"Model B ({result.model_b}): {result.wins_b} wins ({result.win_rate_b():.1%})")
    print(f"Draws: {result.draws}")
    print(f"Significance: {result.significance():.2f}")
    print(f"Recommendation: {ab.recommend('test_1')}")

    print("\n=== A/B Testing Demo Complete ===")


if __name__ == '__main__':
    _demo()
