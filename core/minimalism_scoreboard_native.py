"""
minimalism_scoreboard_native.py
MAGNATRIX-OS — Minimalism Scoreboard

Inspired by Ponytail: Track LOC reduction, feature deferral, and code simplicity impact. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class MinimalismScore:
    score_id: str
    task: str
    loc_before: int
    loc_after: int
    loc_saved: int
    features_deferred: int
    features_rejected: int
    simplicity_rating: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MinimalismScoreboard:
    """Track LOC reduction and code simplicity impact."""

    def __init__(self, cache_dir: str = "./minimalism_scores"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.scores: Dict[str, MinimalismScore] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "scores.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        self.scores[sid] = MinimalismScore(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "scores.json", "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self.scores.items()}, f, indent=2)

    def record(self, score_id: str, task: str, loc_before: int, loc_after: int,
               features_deferred: int = 0, features_rejected: int = 0) -> MinimalismScore:
        loc_saved = loc_before - loc_after
        simplicity = min(1.0, max(0.0, loc_saved / max(1, loc_before) + features_rejected * 0.1))
        score = MinimalismScore(
            score_id=score_id, task=task, loc_before=loc_before, loc_after=loc_after,
            loc_saved=max(0, loc_saved), features_deferred=features_deferred,
            features_rejected=features_rejected, simplicity_rating=round(simplicity, 2),
        )
        self.scores[score_id] = score
        self._save()
        return score

    def leaderboard(self) -> List[MinimalismScore]:
        return sorted(self.scores.values(), key=lambda x: x.simplicity_rating, reverse=True)[:10]

    def total_impact(self) -> Dict[str, Any]:
        total_saved = sum(s.loc_saved for s in self.scores.values())
        total_deferred = sum(s.features_deferred for s in self.scores.values())
        total_rejected = sum(s.features_rejected for s in self.scores.values())
        avg_simplicity = sum(s.simplicity_rating for s in self.scores.values()) / max(1, len(self.scores))
        return {
            "total_loc_saved": total_saved, "total_deferred": total_deferred,
            "total_rejected": total_rejected, "avg_simplicity": round(avg_simplicity, 2),
            "tasks": len(self.scores),
        }

    def get_stats(self) -> Dict[str, Any]:
        return self.total_impact()

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MinimalismScoreboard", "MinimalismScore"]