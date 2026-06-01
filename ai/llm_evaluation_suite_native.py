#!/usr/bin/env python3
"""
ai/llm_evaluation_suite_native.py
MAGNATRIX-OS — Evaluation Suite for the LLM Arena
AMATI pattern: benchmark automation, scoring, regression detection, leaderboard

Pure Python, stdlib only. Simulates benchmark loading, task running,
scoring, and report generation.
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


# ───────────────────────────────────────────────────────────────
# 1. BENCHMARK LOADER
# ───────────────────────────────────────────────────────────────

@dataclass
class BenchmarkTask:
    task_id: str
    suite: str
    prompt: str
    expected: str
    tags: List[str] = field(default_factory=list)
    weight: float = 1.0


class BenchmarkLoader:
    """Load benchmark datasets with normalized format."""

    SUITES = {
        "default": [
            BenchmarkTask("t1", "default", "What is 2+2?", "4", ["math"]),
            BenchmarkTask("t2", "default", "Capital of France?", "Paris", ["geography"]),
            BenchmarkTask("t3", "default", "Reverse 'hello'", "olleh", ["coding"]),
            BenchmarkTask("t4", "default", "What is AI?", "artificial intelligence", ["reasoning"]),
            BenchmarkTask("t5", "default", "Sum of 1 to 10", "55", ["math"]),
        ],
        "coding": [
            BenchmarkTask("c1", "coding", "Write function to add two numbers.", "def add(a,b): return a+b", ["function"]),
            BenchmarkTask("c2", "coding", "Write function to reverse a string.", "def reverse(s): return s[::-1]", ["string"]),
        ],
        "reasoning": [
            BenchmarkTask("r1", "reasoning", "If A > B and B > C, is A > C?", "yes", ["logic"]),
            BenchmarkTask("r2", "reasoning", "Three people cross a bridge... min time?", "17", ["puzzle"]),
        ],
    }

    def load(self, suite_name: str = "default") -> List[BenchmarkTask]:
        return self.SUITES.get(suite_name, [])

    def list_suites(self) -> List[str]:
        return list(self.SUITES.keys())


# ───────────────────────────────────────────────────────────────
# 2. TASK RUNNER
# ───────────────────────────────────────────────────────────────

class TaskRunner:
    """Run benchmark tasks against arena models."""

    def run(self, task: BenchmarkTask, model_id: str = "magnatrix-7b") -> Dict[str, Any]:
        t0 = _now()
        # Simulate model response
        accuracy = random.uniform(0.6, 0.95)
        latency = random.uniform(0.1, 2.0)
        response = f"Simulated response for {task.task_id}"
        return {
            "task_id": task.task_id,
            "model_id": model_id,
            "response": response,
            "accuracy": round(accuracy, 3),
            "latency_ms": round(latency * 1000, 1),
            "tokens": len(task.prompt) // 4 + 20,
        }

    def run_suite(self, tasks: List[BenchmarkTask], model_id: str = "magnatrix-7b") -> List[Dict[str, Any]]:
        return [self.run(t, model_id) for t in tasks]


# ───────────────────────────────────────────────────────────────
# 3. SCORING ENGINE
# ───────────────────────────────────────────────────────────────

class ScoringEngine:
    """Auto-score responses with multiple methods."""

    def score_exact(self, response: str, expected: str) -> float:
        return 1.0 if expected.lower() in response.lower() else 0.0

    def score_semantic(self, response: str, expected: str) -> float:
        # Simulated semantic similarity
        words_r = set(response.lower().split())
        words_e = set(expected.lower().split())
        if not words_e:
            return 0.0
        overlap = len(words_r & words_e)
        return round(overlap / len(words_e), 3)

    def score(self, result: Dict[str, Any], task: BenchmarkTask) -> Dict[str, Any]:
        exact = self.score_exact(result["response"], task.expected)
        semantic = self.score_semantic(result["response"], task.expected)
        accuracy = result["accuracy"]
        combined = (exact * 0.3 + semantic * 0.3 + accuracy * 0.4)
        return {
            "task_id": task.task_id,
            "exact_match": exact,
            "semantic": semantic,
            "accuracy": accuracy,
            "combined": round(combined, 3),
        }


# ───────────────────────────────────────────────────────────────
# 4. METRIC AGGREGATOR
# ───────────────────────────────────────────────────────────────

class MetricAggregator:
    """Aggregate scores per benchmark."""

    def aggregate(self, scores: List[Dict[str, Any]], tasks: List[BenchmarkTask]) -> Dict[str, Any]:
        if not scores:
            return {}
        combined_scores = [s["combined"] for s in scores]
        return {
            "tasks_evaluated": len(scores),
            "pass_rate": round(sum(1 for s in scores if s["combined"] >= 0.7) / len(scores), 3),
            "avg_accuracy": round(sum(s["accuracy"] for s in scores) / len(scores), 3),
            "avg_combined": round(sum(combined_scores) / len(scores), 3),
            "p50": round(sorted(combined_scores)[len(scores) // 2], 3),
            "p95": round(sorted(combined_scores)[int(len(scores) * 0.95)], 3) if len(scores) > 1 else combined_scores[0],
        }

    def per_tag(self, scores: List[Dict[str, Any]], tasks: List[BenchmarkTask]) -> Dict[str, Any]:
        tag_scores: Dict[str, List[float]] = {}
        for s, t in zip(scores, tasks):
            for tag in t.tags:
                tag_scores.setdefault(tag, []).append(s["combined"])
        return {tag: round(sum(vals) / len(vals), 3) for tag, vals in tag_scores.items()}


# ───────────────────────────────────────────────────────────────
# 5. REGRESSION DETECTOR
# ───────────────────────────────────────────────────────────────

class RegressionDetector:
    """Compare current vs previous runs, detect score drops."""

    def __init__(self) -> None:
        self._history: List[Dict[str, Any]] = []

    def record(self, suite_name: str, metrics: Dict[str, Any]) -> None:
        self._history.append({"suite": suite_name, "metrics": metrics, "timestamp": _now()})

    def detect(self, suite_name: str, current_metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        prev = [h for h in self._history if h["suite"] == suite_name]
        if not prev:
            return None
        last = prev[-1]["metrics"]
        current_avg = current_metrics.get("avg_combined", 0)
        prev_avg = last.get("avg_combined", 0)
        if current_avg < prev_avg - 0.05:
            return {
                "regression": True,
                "suite": suite_name,
                "previous_avg": prev_avg,
                "current_avg": current_avg,
                "drop": round(prev_avg - current_avg, 3),
            }
        return None


# ───────────────────────────────────────────────────────────────
# 6. LEADERBOARD
# ───────────────────────────────────────────────────────────────

class Leaderboard:
    """Maintain ranked leaderboard per benchmark."""

    def __init__(self) -> None:
        self._scores: Dict[str, Dict[str, float]] = {}  # suite -> {model_id: score}

    def record(self, suite_name: str, model_id: str, score: float) -> None:
        self._scores.setdefault(suite_name, {})[model_id] = score

    def get_ranking(self, suite_name: str) -> List[Tuple[str, float]]:
        scores = self._scores.get(suite_name, {})
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def get_leader(self, suite_name: str) -> Optional[Tuple[str, float]]:
        ranking = self.get_ranking(suite_name)
        return ranking[0] if ranking else None


# ───────────────────────────────────────────────────────────────
# 7. REPORT GENERATOR
# ───────────────────────────────────────────────────────────────

class ReportGenerator:
    """Generate text reports from evaluation results."""

    def generate_text(self, suite_name: str, metrics: Dict[str, Any], tag_scores: Dict[str, Any], leaderboard: Leaderboard) -> str:
        lines = [
            f"Evaluation Report: {suite_name}",
            "=" * 40,
            f"Tasks evaluated: {metrics['tasks_evaluated']}",
            f"Pass rate: {metrics['pass_rate']:.1%}",
            f"Avg accuracy: {metrics['avg_accuracy']:.3f}",
            f"Avg combined: {metrics['avg_combined']:.3f}",
            f"P50: {metrics['p50']:.3f}",
            f"P95: {metrics['p95']:.3f}",
            "",
            "Per-tag scores:",
        ]
        for tag, score in tag_scores.items():
            lines.append(f"  {tag}: {score:.3f}")
        lines.extend(["", "Leaderboard:"])
        for rank, (model_id, score) in enumerate(leaderboard.get_ranking(suite_name), 1):
            lines.append(f"  {rank}. {model_id}: {score:.3f}")
        return "\n".join(lines)

    def generate_json(self, suite_name: str, metrics: Dict[str, Any], tag_scores: Dict[str, Any], leaderboard: Leaderboard) -> str:
        return json.dumps({
            "suite": suite_name,
            "metrics": metrics,
            "tag_scores": tag_scores,
            "leaderboard": {suite_name: leaderboard.get_ranking(suite_name)},
        }, indent=2)


# ───────────────────────────────────────────────────────────────
# 8. EVALUATION SUITE
# ───────────────────────────────────────────────────────────────

class NativeEvalSuite:
    """Main orchestrator: load -> run -> score -> aggregate -> detect -> report."""

    def __init__(self) -> None:
        self.loader = BenchmarkLoader()
        self.runner = TaskRunner()
        self.scorer = ScoringEngine()
        self.aggregator = MetricAggregator()
        self.regression = RegressionDetector()
        self.leaderboard = Leaderboard()
        self.reports = ReportGenerator()

    def evaluate(self, suite_name: str = "default", model_id: str = "magnatrix-7b") -> Tuple[str, str]:
        tasks = self.loader.load(suite_name)
        if not tasks:
            return f"No tasks in suite: {suite_name}", "{}"

        results = self.runner.run_suite(tasks, model_id)
        scores = [self.scorer.score(r, t) for r, t in zip(results, tasks)]
        metrics = self.aggregator.aggregate(scores, tasks)
        tag_scores = self.aggregator.per_tag(scores, tasks)

        self.leaderboard.record(suite_name, model_id, metrics["avg_combined"])
        reg = self.regression.detect(suite_name, metrics)
        self.regression.record(suite_name, metrics)

        text_report = self.reports.generate_text(suite_name, metrics, tag_scores, self.leaderboard)
        json_report = self.reports.generate_json(suite_name, metrics, tag_scores, self.leaderboard)

        if reg:
            text_report += f"\n\n⚠️ REGRESSION DETECTED: {reg['drop']:.3f} drop in {suite_name}"

        return text_report, json_report

    def stats(self) -> Dict[str, Any]:
        return {
            "suites": self.loader.list_suites(),
            "leaderboards": {k: len(v) for k, v in self.leaderboard._scores.items()},
        }


# ───────────────────────────────────────────────────────────────
# 9. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Evaluation Suite Demo")
    print("=" * 60)

    suite = NativeEvalSuite()

    for suite_name in suite.loader.list_suites():
        print(f"\n--- Evaluating: {suite_name} ---")
        text, json_report = suite.evaluate(suite_name, model_id="magnatrix-7b")
        print(text)

    print(f"\n[STATS] {json.dumps(suite.stats(), indent=2)}")

    print("\n" + "=" * 60)
    print("Demo complete. Evaluation Suite ready for LLM Arena.")
    print("=" * 60)
