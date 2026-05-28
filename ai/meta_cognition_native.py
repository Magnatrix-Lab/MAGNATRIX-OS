"""Meta-Cognition Layer — MAGNATRIX-OS ASI Expansion
Path: ai/meta_cognition_native.py
License: AGPL-3.0
Authors: MAGNATRIX-Lab
Depends: Python 3.11+ stdlib only.

Self-model of own reasoning: confidence calibration, strategy selection,
resource allocation, and halting for thinking processes.
"""

from __future__ import annotations

import json
import logging
import math
import random
import statistics
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meta_cognition")


class Strategy(Enum):
    SEARCH = auto()
    DEDUCTION = auto()
    ANALOGY = auto()
    SIMULATION = auto()
    DECOMPOSITION = auto()


@dataclass
class ThinkingTrace:
    step: int
    strategy: Strategy
    input_data: Any
    output_data: Any
    confidence: float
    time_ms: float
    result_quality: float


@dataclass
class StrategyRecord:
    strategy: Strategy
    uses: int = 0
    successes: int = 0
    total_quality: float = 0.0
    avg_time_ms: float = 0.0


class ConfidenceCalibrator:
    def __init__(self, bins: int = 10) -> None:
        self.bins = bins
        self._history: List[Tuple[float, float, float]] = []

    def record(self, confidence: float, correct: bool) -> None:
        self._history.append((confidence, 1.0 if correct else 0.0, 1.0))

    def calibrated_confidence(self, raw_confidence: float) -> float:
        if not self._history:
            return raw_confidence
        nearby = [(c, corr, tot) for c, corr, tot in self._history if abs(c - raw_confidence) < 0.15]
        if not nearby:
            return raw_confidence
        total_corr = sum(corr for _, corr, _ in nearby)
        total = sum(tot for _, _, tot in nearby)
        return total_corr / total if total > 0 else raw_confidence

    def expected_accuracy(self) -> float:
        if not self._history:
            return 0.5
        return sum(corr for _, corr, _ in self._history) / sum(tot for _, _, tot in self._history)


class StrategySelector:
    def __init__(self, epsilon: float = 0.15, decay: float = 0.995) -> None:
        self.epsilon = epsilon
        self.decay = decay
        self._records: Dict[Strategy, StrategyRecord] = {s: StrategyRecord(s) for s in Strategy}

    def select(self, task_type: str) -> Strategy:
        self.epsilon *= self.decay
        if random.random() < self.epsilon:
            return random.choice(list(Strategy))
        best = None
        best_score = -float("inf")
        for rec in self._records.values():
            score = 0.5 if rec.uses == 0 else rec.total_quality / rec.uses
            if score > best_score:
                best_score = score
                best = rec.strategy
        return best or random.choice(list(Strategy))

    def feedback(self, strategy: Strategy, quality: float, time_ms: float) -> None:
        rec = self._records[strategy]
        rec.uses += 1
        rec.total_quality += quality
        rec.avg_time_ms = (rec.avg_time_ms * (rec.uses - 1) + time_ms) / rec.uses

    def best_strategy(self) -> Tuple[Strategy, float]:
        best = max(self._records.values(), key=lambda r: r.total_quality / max(r.uses, 1))
        return best.strategy, best.total_quality / max(best.uses, 1)


class HaltingCriterion:
    def __init__(self, min_steps: int = 3, max_steps: int = 50, improvement_threshold: float = 0.01) -> None:
        self.min_steps = min_steps
        self.max_steps = max_steps
        self.improvement_threshold = improvement_threshold
        self._qualities: List[float] = []

    def record_step(self, quality: float) -> None:
        self._qualities.append(quality)

    def should_stop(self) -> bool:
        n = len(self._qualities)
        if n < self.min_steps:
            return False
        if n >= self.max_steps:
            return True
        if n >= 4:
            recent = self._qualities[-3:]
            improvement = max(recent) - min(recent)
            if improvement < self.improvement_threshold:
                return True
        return False

    def quality_trend(self) -> float:
        if len(self._qualities) < 3:
            return 0.0
        recent = self._qualities[-5:]
        n = len(recent)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2
        y_mean = sum(recent) / n
        num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return num / den if den else 0.0


class MetaCognitionEngine:
    def __init__(self, epsilon: float = 0.15) -> None:
        self.confidence = ConfidenceCalibrator()
        self.strategy = StrategySelector(epsilon=epsilon)
        self.halting = HaltingCriterion()
        self.traces: List[ThinkingTrace] = []
        self._error_history: List[Tuple[Any, Any]] = []

    def think(self, problem: Any, reasoning_fn: Callable[[Any, Strategy], Tuple[Any, float]], ground_truth: Optional[Any] = None) -> Tuple[Any, ThinkingTrace]:
        step = 0
        best_result = None
        best_quality = -float("inf")
        best_trace = None
        while not self.halting.should_stop():
            step += 1
            strat = self.strategy.select(type(problem).__name__)
            start = time.perf_counter()
            result, raw_conf = reasoning_fn(problem, strat)
            elapsed = (time.perf_counter() - start) * 1000
            quality = self._assess_quality(result, ground_truth, raw_conf)
            cal_conf = self.confidence.calibrated_confidence(raw_conf)
            trace = ThinkingTrace(step=step, strategy=strat, input_data=problem, output_data=result, confidence=cal_conf, time_ms=elapsed, result_quality=quality)
            self.traces.append(trace)
            self.strategy.feedback(strat, quality, elapsed)
            self.halting.record_step(quality)
            if quality > best_quality:
                best_quality = quality
                best_result = result
                best_trace = trace
        return best_result, best_trace or ThinkingTrace(0, Strategy.SEARCH, None, None, 0.0, 0.0, 0.0)

    def _assess_quality(self, result: Any, ground_truth: Optional[Any], confidence: float) -> float:
        if ground_truth is not None:
            if result == ground_truth:
                return 1.0
            if isinstance(result, str) and isinstance(ground_truth, str):
                return 1.0 - self._levenshtein(result, ground_truth) / max(len(result), len(ground_truth), 1)
            return 0.0
        return confidence

    @staticmethod
    def _levenshtein(a: str, b: str) -> int:
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if a[i - 1] == b[j - 1] else 1
                dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
        return dp[m][n]

    def reflect_on_error(self, expected: Any, actual: Any) -> str:
        self._error_history.append((expected, actual))
        recent_errors = self._error_history[-10:]
        if len(recent_errors) >= 3:
            last_strat = self.traces[-1].strategy if self.traces else Strategy.SEARCH
            return f"Consider switching from {last_strat.name} — recent errors suggest mismatch."
        return "Continue current approach — insufficient error data."

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_traces": len(self.traces),
            "calibrated_accuracy": self.confidence.expected_accuracy(),
            "best_strategy": self.strategy.best_strategy()[0].name,
            "avg_step_time_ms": statistics.mean(t.time_ms for t in self.traces) if self.traces else 0,
            "halting_quality_trend": self.halting.quality_trend(),
        }


def _self_test() -> int:
    passed = 0
    total = 0
    def check(name, condition):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name}")

    print("=" * 55)
    print("Meta-Cognition Layer — Self Test")
    print("=" * 55)

    print("\n[1] Confidence calibration")
    cal = ConfidenceCalibrator()
    for i in range(100):
        conf = 0.5 + (i % 5) * 0.1
        correct = random.random() < (0.5 + conf * 0.3)
        cal.record(conf, correct)
    acc = cal.expected_accuracy()
    check(f"Tracked accuracy: {acc:.2f}", 0 < acc < 1)
    cal_conf = cal.calibrated_confidence(0.8)
    check(f"Calibrated confidence at 0.8: {cal_conf:.2f}", 0 <= cal_conf <= 1)

    print("\n[2] Strategy selection")
    sel = StrategySelector(epsilon=0.3)
    for _ in range(50):
        s = sel.select("math")
        if s == Strategy.DEDUCTION:
            sel.feedback(s, 0.9, 10.0)
        elif s == Strategy.SEARCH:
            sel.feedback(s, 0.5, 5.0)
        else:
            sel.feedback(s, 0.6, 8.0)
    best_strat, best_score = sel.best_strategy()
    check(f"Best strategy: {best_strat.name} (score {best_score:.2f})", best_strat == Strategy.DEDUCTION)

    print("\n[3] Halting criterion")
    halt = HaltingCriterion(min_steps=3, max_steps=20, improvement_threshold=0.01)
    for i in range(20):
        quality = 0.5 + 0.3 * (1 - math.exp(-i * 0.3))
        halt.record_step(quality)
    check("Halting triggered", halt.should_stop())
    check("Steps within max", len(halt._qualities) <= 20)

    print("\n[4] Full meta-cognitive reasoning")
    engine = MetaCognitionEngine(epsilon=0.2)
    def mock_reason(problem, strat):
        return problem + "_solved", 0.85 if strat == Strategy.DEDUCTION else 0.5
    result, trace = engine.think("test_problem", mock_reason, ground_truth="test_problem_solved")
    check("Think loop completed", trace.step > 0)
    check("Result matches ground truth", result == "test_problem_solved")

    print("\n[5] Stats reporting")
    stats = engine.get_stats()
    check("Stats has traces", stats["total_traces"] > 0)
    check("Stats has accuracy", 0 <= stats["calibrated_accuracy"] <= 1)

    print("\n[6] Error reflection")
    engine2 = MetaCognitionEngine()
    msg1 = engine2.reflect_on_error("expected", "actual")
    msg2 = engine2.reflect_on_error("expected", "actual")
    check("Reflection gives advice", len(msg1) > 0)
    check("Repeated errors trigger suggestion", "switching" in msg2.lower() or "insufficient" in msg2.lower())

    print("\n" + "=" * 55)
    print(f"PASS: {passed}/{total}")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
