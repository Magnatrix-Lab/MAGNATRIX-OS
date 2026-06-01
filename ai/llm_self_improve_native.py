#!/usr/bin/env python3
"""
ai/llm_self_improve_native.py
MAGNATRIX-OS — Self-Improvement Loop for the LLM Arena
AMATI pattern: self-evolving AI, continuous learning, feedback loops

Pure Python, stdlib only. Simulates tournament analysis, strategy optimization,
synthetic data generation, and knowledge distillation.
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


def _short_hash(text: str) -> str:
    return str(hash(text) & 0xFFFFFFFF)[:8]


# ───────────────────────────────────────────────────────────────
# 1. TOURNAMENT ANALYZER
# ───────────────────────────────────────────────────────────────

class TournamentAnalyzer:
    """Analyze tournament history, identify win patterns per task type."""

    def __init__(self) -> None:
        self.history: List[Dict[str, Any]] = []

    def record_match(self, model_id: str, task_type: str, won: bool, score: float, strategy: str) -> None:
        self.history.append({
            "model_id": model_id, "task_type": task_type, "won": won,
            "score": score, "strategy": strategy, "timestamp": _now(),
        })

    def win_rate_matrix(self) -> Dict[str, Dict[str, Any]]:
        matrix: Dict[str, Dict[str, Any]] = {}
        for h in self.history:
            mid = h["model_id"]
            if mid not in matrix:
                matrix[mid] = {"wins": 0, "losses": 0, "by_task": {}, "avg_score": 0.0, "matches": 0}
            matrix[mid]["matches"] += 1
            if h["won"]:
                matrix[mid]["wins"] += 1
            else:
                matrix[mid]["losses"] += 1
            matrix[mid]["avg_score"] = (matrix[mid]["avg_score"] * (matrix[mid]["matches"] - 1) + h["score"]) / matrix[mid]["matches"]
            tt = h["task_type"]
            if tt not in matrix[mid]["by_task"]:
                matrix[mid]["by_task"][tt] = {"wins": 0, "matches": 0}
            matrix[mid]["by_task"][tt]["matches"] += 1
            if h["won"]:
                matrix[mid]["by_task"][tt]["wins"] += 1
        return matrix

    def best_model_per_task(self) -> Dict[str, str]:
        matrix = self.win_rate_matrix()
        best = {}
        for task in set(tt for m in matrix.values() for tt in m.get("by_task", {})):
            candidates = [(mid, m["by_task"][task]["wins"] / max(m["by_task"][task]["matches"], 1)) for mid, m in matrix.items() if task in m.get("by_task", {})]
            if candidates:
                best[task] = max(candidates, key=lambda x: x[1])[0]
        return best

    def stats(self) -> Dict[str, Any]:
        return {"total_matches": len(self.history), "models": len(set(h["model_id"] for h in self.history))}


# ───────────────────────────────────────────────────────────────
# 2. STRATEGY OPTIMIZER
# ───────────────────────────────────────────────────────────────

class StrategyOptimizer:
    """Auto-adjust ensemble strategy weights based on historical performance."""

    STRATEGIES = ["best_single", "majority", "weighted", "consensus", "debate", "cascade"]

    def __init__(self) -> None:
        self.weights: Dict[str, float] = {s: 1.0 / len(self.STRATEGIES) for s in self.STRATEGIES}
        self.history: Dict[str, List[float]] = {s: [] for s in self.STRATEGIES}

    def record(self, strategy: str, score: float) -> None:
        self.history[strategy].append(score)
        if len(self.history[strategy]) > 20:
            self.history[strategy].pop(0)
        self._rebalance()

    def _rebalance(self) -> None:
        avg_scores = {s: sum(self.history[s]) / max(len(self.history[s]), 1) for s in self.STRATEGIES}
        total = sum(avg_scores.values())
        if total > 0:
            self.weights = {s: avg_scores[s] / total for s in self.STRATEGIES}

    def recommend(self, task_type: str) -> str:
        return max(self.weights, key=self.weights.get) if self.weights else "cascade"

    def get_weights(self) -> Dict[str, float]:
        return {k: round(v, 4) for k, v in self.weights.items()}


# ───────────────────────────────────────────────────────────────
# 3. SYNTHETIC GENERATOR
# ───────────────────────────────────────────────────────────────

class SyntheticGenerator:
    """Generate high-quality training prompts from winning responses."""

    TEMPLATES = {
        "reasoning": [
            "Explain why {concept} works using first principles.",
            "Compare and contrast {a} and {b} in the context of {domain}.",
        ],
        "coding": [
            "Write a {language} function that {task}. Include error handling.",
            "Debug this code: {code_snippet}",
        ],
        "math": [
            "Solve for x: {equation}",
            "Prove that {theorem} holds under {condition}.",
        ],
        "writing": [
            "Write a {style} piece about {topic} in {tone} tone.",
        ],
    }

    def __init__(self) -> None:
        self.generated: List[Dict[str, Any]] = []

    def generate(self, task_type: str, count: int = 3, difficulty: int = 1) -> List[Dict[str, Any]]:
        templates = self.TEMPLATES.get(task_type, self.TEMPLATES["reasoning"])
        samples = []
        for i in range(count):
            template = random.choice(templates)
            prompt = template.format(
                concept=f"concept_{i}", a=f"A{i}", b=f"B{i}", domain=f"domain_{i}",
                language="Python", task=f"task_{i}", code_snippet="x = 1 / 0",
                equation=f"2x + {i} = 10", theorem=f"theorem_{i}", condition=f"condition_{i}",
                style="essay", topic=f"topic_{i}", tone="professional",
            )
            samples.append({
                "prompt": prompt,
                "task_type": task_type,
                "difficulty": difficulty,
                "quality_score": round(0.7 + random.random() * 0.3, 3),
                "generated_at": _now(),
            })
        self.generated.extend(samples)
        return samples

    def stats(self) -> Dict[str, Any]:
        return {"total_generated": len(self.generated), "by_task": {}}


# ───────────────────────────────────────────────────────────────
# 4. FEEDBACK LOOP
# ───────────────────────────────────────────────────────────────

class FeedbackLoop:
    """Collect user feedback, update model capability scores."""

    def __init__(self) -> None:
        self.feedbacks: List[Dict[str, Any]] = []
        self.model_scores: Dict[str, float] = {}

    def add_explicit(self, model_id: str, rating: int, comment: str = "") -> None:
        self.feedbacks.append({"model_id": model_id, "rating": rating, "comment": comment, "type": "explicit", "timestamp": _now()})
        self._update(model_id, rating / 5.0)

    def add_implicit(self, model_id: str, accepted: bool, edit_distance: int = 0) -> None:
        score = 1.0 if accepted else max(0.0, 1.0 - edit_distance / 100)
        self.feedbacks.append({"model_id": model_id, "accepted": accepted, "score": score, "type": "implicit", "timestamp": _now()})
        self._update(model_id, score)

    def _update(self, model_id: str, score: float) -> None:
        alpha = 0.3
        current = self.model_scores.get(model_id, 0.5)
        self.model_scores[model_id] = round(current + alpha * (score - current), 4)

    def get_scores(self) -> Dict[str, float]:
        return self.model_scores.copy()

    def stats(self) -> Dict[str, Any]:
        return {"total_feedback": len(self.feedbacks), "models_rated": len(self.model_scores)}


# ───────────────────────────────────────────────────────────────
# 5. AUTO BENCHMARK
# ───────────────────────────────────────────────────────────────

class AutoBenchmark:
    """Run periodic benchmark suites, detect regressions."""

    BENCHMARKS = {
        "mmlu": {"description": "Massive Multitask Language Understanding", "weight": 0.3},
        "human_eval": {"description": "Code generation benchmark", "weight": 0.25},
        "gsm8k": {"description": "Grade school math", "weight": 0.2},
        "mt_bench": {"description": "Multi-turn conversation", "weight": 0.15},
        "truthfulqa": {"description": "Truthfulness", "weight": 0.1},
    }

    def __init__(self) -> None:
        self.runs: List[Dict[str, Any]] = []

    def run(self, model_id: str) -> Dict[str, Any]:
        scores = {}
        for name, meta in self.BENCHMARKS.items():
            scores[name] = round(random.uniform(0.6, 0.95), 3)
        weighted = sum(scores[n] * meta["weight"] for n, meta in self.BENCHMARKS.items())
        run = {
            "model_id": model_id,
            "scores": scores,
            "weighted_average": round(weighted, 3),
            "timestamp": _now(),
        }
        self.runs.append(run)
        return run

    def detect_regression(self, model_id: str) -> Optional[Dict[str, Any]]:
        model_runs = [r for r in self.runs if r["model_id"] == model_id]
        if len(model_runs) < 2:
            return None
        latest = model_runs[-1]["weighted_average"]
        previous = model_runs[-2]["weighted_average"]
        if latest < previous - 0.05:
            return {"model_id": model_id, "previous": previous, "latest": latest, "drop": round(previous - latest, 3)}
        return None

    def stats(self) -> Dict[str, Any]:
        return {"total_runs": len(self.runs), "benchmarks": len(self.BENCHMARKS)}


# ───────────────────────────────────────────────────────────────
# 6. KNOWLEDGE DISTILLER
# ───────────────────────────────────────────────────────────────

class KnowledgeDistiller:
    """Distill learnings from ensemble into rules for future routing."""

    def __init__(self) -> None:
        self.rules: List[Dict[str, Any]] = []

    def distill(self, analyzer: TournamentAnalyzer, optimizer: StrategyOptimizer) -> List[Dict[str, Any]]:
        best_per_task = analyzer.best_model_per_task()
        weights = optimizer.get_weights()
        new_rules = []
        for task, model in best_per_task.items():
            new_rules.append({
                "rule": f"Use {model} for {task} tasks",
                "confidence": round(weights.get("cascade", 0.5), 3),
                "source": "tournament_analysis",
                "created_at": _now(),
            })
        self.rules.extend(new_rules)
        return new_rules

    def get_rules(self) -> List[Dict[str, Any]]:
        return self.rules

    def stats(self) -> Dict[str, Any]:
        return {"total_rules": len(self.rules), "categories": list(set(r.get("source") for r in self.rules))}


# ───────────────────────────────────────────────────────────────
# 7. SELF-IMPROVEMENT ENGINE
# ───────────────────────────────────────────────────────────────

class SelfImprovementEngine:
    """Main orchestrator: analyze -> optimize -> generate -> feedback -> benchmark -> distill."""

    def __init__(self) -> None:
        self.analyzer = TournamentAnalyzer()
        self.optimizer = StrategyOptimizer()
        self.generator = SyntheticGenerator()
        self.feedback = FeedbackLoop()
        self.benchmark = AutoBenchmark()
        self.distiller = KnowledgeDistiller()
        self.cycle_count = 0

    def cycle(self, model_id: str, task_type: str, won: bool, score: float, strategy: str) -> Dict[str, Any]:
        self.cycle_count += 1

        self.analyzer.record_match(model_id, task_type, won, score, strategy)
        matrix = self.analyzer.win_rate_matrix()

        self.optimizer.record(strategy, score)

        samples = self.generator.generate(task_type, count=2, difficulty=min(self.cycle_count, 5))

        bench = self.benchmark.run(model_id)
        regression = self.benchmark.detect_regression(model_id)

        rules = self.distiller.distill(self.analyzer, self.optimizer)

        return {
            "cycle": self.cycle_count,
            "model_id": model_id,
            "win_rate_matrix": {k: {"wins": v["wins"], "losses": v["losses"], "avg_score": round(v["avg_score"], 3)} for k, v in matrix.items()},
            "strategy_weights": self.optimizer.get_weights(),
            "synthetic_samples": len(samples),
            "benchmark": bench,
            "regression": regression,
            "rules_distilled": len(rules),
            "timestamp": _now(),
        }

    def full_report(self) -> Dict[str, Any]:
        return {
            "cycles": self.cycle_count,
            "analyzer": self.analyzer.stats(),
            "optimizer": self.optimizer.get_weights(),
            "generator": self.generator.stats(),
            "feedback": self.feedback.stats(),
            "benchmark": self.benchmark.stats(),
            "distiller": self.distiller.stats(),
        }


# ───────────────────────────────────────────────────────────────
# 8. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Self-Improvement Engine Demo")
    print("=" * 60)

    engine = SelfImprovementEngine()

    models = ["claude-3-5-sonnet", "gpt-4o", "gemini-1.5-pro", "deepseek-v2"]
    tasks = ["reasoning", "coding", "math", "writing"]
    strategies = ["best_single", "weighted", "cascade", "debate"]

    print("\n[1] Running 12 improvement cycles...")
    for i in range(12):
        model = random.choice(models)
        task = random.choice(tasks)
        won = random.random() > 0.3
        score = round(random.uniform(0.7, 0.95), 3)
        strategy = random.choice(strategies)
        result = engine.cycle(model, task, won, score, strategy)
        if i < 3 or i == 11:
            print(f"  Cycle {result['cycle']}: {model} on {task} -> {'win' if won else 'loss'} (score {score})")
            print(f"    Strategy weights: {result['strategy_weights']}")
            print(f"    Rules distilled: {result['rules_distilled']}")
            if result['regression']:
                print(f"    ⚠️ REGRESSION: {result['regression']}")

    print("\n[2] Full Report")
    report = engine.full_report()
    print(f"  {json.dumps(report, indent=2)}")

    print("\n[3] Best Model Per Task")
    best = engine.analyzer.best_model_per_task()
    for task, model in best.items():
        print(f"  {task}: {model}")

    print("\n" + "=" * 60)
    print("Demo complete. Self-Improvement Engine ready for LLM Arena.")
    print("=" * 60)
