"""
medical_evaluation_benchmark_native.py
MAGNATRIX-OS — Medical Evaluation Benchmark

Inspired by Meditron (EPFL): MedQA and medical reasoning benchmarks. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class BenchmarkTask:
    task_id: str
    dataset: str  # medqa, medmcqa, pubmedqa, mmlu
    question: str
    options: List[str] = field(default_factory=list)
    correct_answer: str = ""
    subject: str = ""
    difficulty: str = "medium"


@dataclass
class BenchmarkRun:
    run_id: str
    model_id: str
    task_results: Dict[str, bool] = field(default_factory=dict)
    scores: Dict[str, float] = field(default_factory=dict)


class MedicalEvaluationBenchmark:
    """Medical reasoning benchmarks: MedQA, PubMedQA, MMLU-medical."""

    def __init__(self, benchmark_dir: str = "./medical_benchmarks"):
        self.benchmark_dir = Path(benchmark_dir)
        self.benchmark_dir.mkdir(exist_ok=True)
        self.tasks: Dict[str, BenchmarkTask] = {}
        self.runs: Dict[str, BenchmarkRun] = {}
        self._load()

    def _load(self) -> None:
        for fname in ["tasks.json", "runs.json"]:
            f = self.benchmark_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "tasks.json":
                            for tid, td in data.items():
                                self.tasks[tid] = BenchmarkTask(**td)
                        else:
                            for rid, rd in data.items():
                                self.runs[rid] = BenchmarkRun(**rd)
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.benchmark_dir / "tasks.json", "w", encoding="utf-8") as f:
            json.dump({tid: asdict(t) for tid, t in self.tasks.items()}, f, indent=2)
        with open(self.benchmark_dir / "runs.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.runs.items()}, f, indent=2)

    def add_task(self, task_id: str, dataset: str, question: str, options: List[str],
                 correct_answer: str, subject: str = "", difficulty: str = "medium") -> BenchmarkTask:
        task = BenchmarkTask(
            task_id=task_id, dataset=dataset, question=question, options=options,
            correct_answer=correct_answer, subject=subject, difficulty=difficulty,
        )
        self.tasks[task_id] = task
        self._save()
        return task

    def run(self, run_id: str, model_id: str) -> BenchmarkRun:
        run = BenchmarkRun(run_id=run_id, model_id=model_id)
        for task_id, task in self.tasks.items():
            # Simulate model answer (random for now)
            import random
            predicted = random.choice(task.options)
            run.task_results[task_id] = predicted == task.correct_answer
        # Calculate scores per dataset
        dataset_scores = {}
        dataset_counts = {}
        for task_id, correct in run.task_results.items():
            task = self.tasks.get(task_id)
            if task:
                dataset_scores[task.dataset] = dataset_scores.get(task.dataset, 0) + (1 if correct else 0)
                dataset_counts[task.dataset] = dataset_counts.get(task.dataset, 0) + 1
        run.scores = {ds: round(dataset_scores[ds] / max(1, dataset_counts[ds]), 4) for ds in dataset_scores}
        self.runs[run_id] = run
        self._save()
        return run

    def evaluate(self, run_id: str) -> Dict[str, Any]:
        run = self.runs.get(run_id)
        if not run:
            return {}
        total = len(run.task_results)
        correct = sum(1 for c in run.task_results.values() if c)
        return {"run_id": run_id, "model": run.model_id, "total": total, "correct": correct, "accuracy": round(correct / max(1, total), 4), "scores_by_dataset": run.scores}

    def get_leaderboard(self, dataset: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for run in self.runs.values():
            score = run.scores.get(dataset, sum(run.scores.values()) / max(1, len(run.scores)))
            results.append({"model": run.model_id, "score": score, "run_id": run.run_id})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:10]

    def get_stats(self) -> Dict[str, Any]:
        return {"tasks": len(self.tasks), "runs": len(self.runs)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MedicalEvaluationBenchmark", "BenchmarkTask", "BenchmarkRun"]