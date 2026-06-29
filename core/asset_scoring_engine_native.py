"""
asset_scoring_engine_native.py
MAGNATRIX-OS — Asset Scoring Engine

Inspired by Frogy2.0: Score and rank discovered assets by risk. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class AssetScore:
    asset_id: str
    risk_score: float
    criticality: str
    exposure_level: str
    findings_count: int
    ranking: int = 0


class AssetScoringEngine:
    """Score and rank discovered assets by risk and exposure."""

    def __init__(self, data_dir: str = "./asset_scores"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.scores: Dict[str, AssetScore] = {}
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "scores.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for aid, sd in data.items():
                        self.scores[aid] = AssetScore(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "scores.json", "w", encoding="utf-8") as f:
            json.dump({aid: asdict(s) for aid, s in self.scores.items()}, f, indent=2)

    def score(self, asset_id: str, open_ports: int = 0, exposed_services: int = 0,
              has_login_panel: bool = False, has_exposed_api: bool = False,
              secrets_found: int = 0, cert_days_remaining: int = 365,
              email_risk: float = 0.0, cloud_exposed: bool = False) -> AssetScore:
        """Calculate risk score for an asset."""
        score = 0.0
        score += open_ports * 0.5
        score += exposed_services * 1.0
        if has_login_panel:
            score += 2.0
        if has_exposed_api:
            score += 1.5
        score += secrets_found * 3.0
        if cert_days_remaining < 30:
            score += 2.0
        elif cert_days_remaining < 7:
            score += 4.0
        score += email_risk
        if cloud_exposed:
            score += 1.5
        criticality = "critical" if score >= 8 else "high" if score >= 5 else "medium" if score >= 2 else "low"
        exposure = "high" if open_ports > 5 or has_exposed_api else "medium" if open_ports > 2 else "low"
        asset_score = AssetScore(
            asset_id=asset_id, risk_score=round(min(score, 10), 2),
            criticality=criticality, exposure_level=exposure,
            findings_count=secrets_found + exposed_services + open_ports,
        )
        self.scores[asset_id] = asset_score
        self._recalculate_rankings()
        self._save()
        return asset_score

    def _recalculate_rankings(self) -> None:
        sorted_scores = sorted(self.scores.values(), key=lambda x: x.risk_score, reverse=True)
        for rank, score in enumerate(sorted_scores, 1):
            score.ranking = rank

    def get_top_risk(self, n: int = 10) -> List[AssetScore]:
        return sorted(self.scores.values(), key=lambda x: x.risk_score, reverse=True)[:n]

    def get_by_criticality(self, level: str) -> List[AssetScore]:
        return [s for s in self.scores.values() if s.criticality == level]

    def get_stats(self) -> Dict[str, Any]:
        by_crit = {}
        for s in self.scores.values():
            by_crit[s.criticality] = by_crit.get(s.criticality, 0) + 1
        avg = sum(s.risk_score for s in self.scores.values()) / max(1, len(self.scores))
        return {"total_scored": len(self.scores), "avg_risk": round(avg, 2), "by_criticality": by_crit}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AssetScoringEngine", "AssetScore"]