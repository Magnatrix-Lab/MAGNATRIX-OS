"""
benchmark_engine_native.py
MAGNATRIX-OS — Benchmark Engine

Inspired by AgentSkillOS: 30 creative tasks with pairwise comparison and Bradley-Terry aggregation. Pure stdlib.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class BenchmarkTask:
    task_id: str
    category: str
    description: str
    format: str
    difficulty: str


@dataclass
class PairwiseResult:
    result_id: str
    task_id: str
    model_a: str
    model_b: str
    winner: str
    confidence: float


class BenchmarkEngine:
    """Benchmark with pairwise comparison and Bradley-Terry aggregation."""

    CATEGORIES = ["bug_diagnosis", "ui_design", "data_analysis", "code_generation", "creative_writing"]

    def __init__(self, cache_dir: str = "./benchmark_engine"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.tasks: Dict[str, BenchmarkTask] = {}
        self.results: List[PairwiseResult] = []
        self.scores: Dict[str, float] = {}
        self._load()
        self._init_tasks()

    def _init_tasks(self) -> None:
        tasks = [
            ("bug_1", "bug_diagnosis", "Mobile bug localization", "report", "medium"),
            ("bug_2", "bug_diagnosis", "Fix validation", "test", "hard"),
            ("bug_3", "bug_diagnosis", "Visual bug report", "image", "medium"),
            ("ui_1", "ui_design", "Design language research", "document", "medium"),
            ("ui_2", "ui_design", "Concept mockups", "image", "hard"),
            ("ui_3", "ui_design", "Responsive layout", "code", "easy"),
            ("data_1", "data_analysis", "Trend analysis", "chart", "medium"),
            ("data_2", "data_analysis", "Correlation discovery", "report", "hard"),
            ("data_3", "data_analysis", "Anomaly detection", "code", "hard"),
            ("code_1", "code_generation", "API endpoint", "code", "easy"),
            ("code_2", "code_generation", "Auth middleware", "code", "medium"),
            ("code_3", "code_generation", "Database migration", "script", "hard"),
            ("creative_1", "creative_writing", "Product description", "text", "easy"),
            ("creative_2", "creative_writing", "Technical blog post", "text", "medium"),
            ("creative_3", "creative_writing", "Marketing copy", "text", "easy"),
        ]
        for tid, cat, desc, fmt, diff in tasks:
            if tid not in self.tasks:
                self.tasks[tid] = BenchmarkTask(task_id=tid, category=cat, description=desc, format=fmt, difficulty=diff)

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.results = [PairwiseResult(**r) for r in data.get("results", [])]
                    self.scores = data.get("scores", {})
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({
                "results": [asdict(r) for r in self.results], "scores": self.scores,
            }, f, indent=2)

    def add_task(self, task_id: str, category: str, description: str, format: str, difficulty: str) -> BenchmarkTask:
        task = BenchmarkTask(task_id=task_id, category=category, description=description, format=format, difficulty=difficulty)
        self.tasks[task_id] = task
        return task

    def record_pairwise(self, result_id: str, task_id: str, model_a: str, model_b: str, winner: str, confidence: float) -> PairwiseResult:
        result = PairwiseResult(
            result_id=result_id, task_id=task_id, model_a=model_a,
            model_b=model_b, winner=winner, confidence=confidence,
        )
        self.results.append(result)
        self._update_bradley_terry()
        self._save()
        return result

    def _update_bradley_terry(self) -> None:
        """Bradley-Terry model for ranking models."""
        models = set()
        for r in self.results:
            models.add(r.model_a)
            models.add(r.model_b)

        wins = {m: 0 for m in models}
        losses = {m: 0 for m in models}

        for r in self.results:
            if r.winner == r.model_a:
                wins[r.model_a] += r.confidence
                losses[r.model_b] += r.confidence
            elif r.winner == r.model_b:
                wins[r.model_b] += r.confidence
                losses[r.model_a] += r.confidence

        for m in models:
            total = wins[m] + losses[m]
            if total > 0:
                self.scores[m] = round(wins[m] / total, 4)
            else:
                self.scores[m] = 0.5

    def leaderboard(self) -> List[tuple]:
        return sorted(self.scores.items(), key=lambda x: x[1], reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.results)
        return {"total_comparisons": total, "models_ranked": len(self.scores), "tasks": len(self.tasks)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["BenchmarkEngine", "BenchmarkTask", "PairwiseResult"]