"""
complexity_assessor_native.py
MAGNATRIX-OS — Complexity Assessor

Inspired by engineering-discipline: Auto-routing complexity assessment (Simple 5-8, Complex 9-15). Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ComplexityScore:
    score_id: str
    request: str
    score: int
    category: str  # simple, moderate, complex
    factors: Dict[str, int]
    routing: str  # direct, plan, milestone


class ComplexityAssessor:
    """Auto-routing complexity assessment for engineering tasks."""

    FACTORS = {
        "lines_of_code": ["LOC estimate", 0, 50, 200, 500, 1000],
        "files_touched": ["Files modified", 0, 1, 3, 5, 10],
        "dependencies": ["New dependencies", 0, 0, 1, 3, 5],
        "test_coverage": ["Test complexity", 0, 1, 2, 4, 8],
        "integration_points": ["Integration points", 0, 0, 1, 2, 5],
        "risk_level": ["Risk level", 0, 1, 2, 3, 5],
    }

    def __init__(self, cache_dir: str = "./complexity_scores"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.scores: Dict[str, ComplexityScore] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "scores.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        self.scores[sid] = ComplexityScore(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "scores.json", "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self.scores.items()}, f, indent=2)

    def assess(self, score_id: str, request: str, factors: Optional[Dict[str, int]] = None) -> ComplexityScore:
        """Assess complexity and route to appropriate workflow."""
        factors = factors or {}
        total = 0
        scored_factors = {}
        for key, default_range in self.FACTORS.items():
            val = factors.get(key, 0)
            # Score 0-5 based on thresholds
            score = 0
            for i, threshold in enumerate(default_range[1:]):
                if val >= threshold:
                    score = i + 1
            scored_factors[key] = score
            total += score

        # Normalize to 5-15 scale
        normalized = max(5, min(15, 5 + total))

        if normalized <= 8:
            category = "simple"
            routing = "direct"
        elif normalized <= 11:
            category = "moderate"
            routing = "plan"
        else:
            category = "complex"
            routing = "milestone"

        result = ComplexityScore(
            score_id=score_id, request=request, score=normalized,
            category=category, factors=scored_factors, routing=routing,
        )
        self.scores[score_id] = result
        self._save()
        return result

    def get_score(self, score_id: str) -> Optional[ComplexityScore]:
        return self.scores.get(score_id)

    def get_stats(self) -> Dict[str, Any]:
        simple = sum(1 for s in self.scores.values() if s.category == "simple")
        moderate = sum(1 for s in self.scores.values() if s.category == "moderate")
        complex_ = sum(1 for s in self.scores.values() if s.category == "complex")
        return {"total": len(self.scores), "simple": simple, "moderate": moderate, "complex": complex_}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ComplexityAssessor", "ComplexityScore"]