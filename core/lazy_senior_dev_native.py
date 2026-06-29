"""
lazy_senior_dev_native.py
MAGNATRIX-OS — Lazy Senior Dev Engine

Inspired by Ponytail: "The laziest correct solution is the best." Code laziness scoring and recommendations. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class LazinessScore:
    task_id: str
    approach: str
    loc: int
    dependencies: int
    stdlib_usage: int
    copy_paste_potential: float
    laziness_score: float
    recommendation: str


class LazySeniorDev:
    """Score and recommend the laziest correct solution."""

    LAZINESS_PRINCIPLES = [
        "Prefer standard library over third-party",
        "Copy-paste existing code over re-implementing",
        "One-liner is better than a function",
        "A function is better than a class",
        "A class is better than a microservice",
        "If it works, ship it",
    ]

    def __init__(self, cache_dir: str = "./lazy_scores"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.scores: Dict[str, LazinessScore] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "scores.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for tid, td in data.items():
                        self.scores[tid] = LazinessScore(**td)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "scores.json", "w", encoding="utf-8") as f:
            json.dump({tid: asdict(s) for tid, s in self.scores.items()}, f, indent=2)

    def score(self, task_id: str, approach: str, loc: int, dependencies: int = 0,
              stdlib_usage: int = 0, existing_patterns: int = 0) -> LazinessScore:
        """Score how "lazy" (efficient) a solution is."""
        score = 0.0
        # Lower LOC = lazier
        score += max(0, 1.0 - loc / 100.0)
        # Fewer dependencies = lazier
        score += max(0, 1.0 - dependencies / 5.0)
        # More stdlib = lazier
        score += min(1.0, stdlib_usage / 5.0)
        # More existing pattern reuse = lazier
        score += min(1.0, existing_patterns / 3.0)
        score = min(1.0, score / 3.0)

        if score > 0.7:
            rec = "Excellent laziness. Ship it."
        elif score > 0.4:
            rec = "Good laziness. Can you simplify further?"
        else:
            rec = "Too much work. Find a lazier way."

        result = LazinessScore(
            task_id=task_id, approach=approach, loc=loc, dependencies=dependencies,
            stdlib_usage=stdlib_usage, copy_paste_potential=round(existing_patterns / max(1, loc), 4),
            laziness_score=round(score, 2), recommendation=rec,
        )
        self.scores[task_id] = result
        self._save()
        return result

    def get_principles(self) -> List[str]:
        return self.LAZINESS_PRINCIPLES

    def get_stats(self) -> Dict[str, Any]:
        avg = sum(s.laziness_score for s in self.scores.values()) / max(1, len(self.scores))
        return {"tasks_scored": len(self.scores), "avg_laziness": round(avg, 2)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["LazySeniorDev", "LazinessScore"]