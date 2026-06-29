"""
agent_critique_analyzer_native.py
MAGNATRIX-OS — Agent Critique Analyzer

Inspired by arXiv 2606.23991: Critique of agent models - agency dimensions analysis. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class AgencyDimension:
    dimension: str
    score: float
    description: str
    is_internalized: bool


class AgentCritiqueAnalyzer:
    """Analyze agent systems across agency dimensions."""

    DIMENSIONS = ["goal", "identity", "decision_making", "self_regulation", "learning"]

    def __init__(self, cache_dir: str = "./agent_critique"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.analyses: Dict[str, List[AgencyDimension]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "analyses.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for aid, alist in data.items():
                        self.analyses[aid] = [AgencyDimension(**a) for a in alist]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "analyses.json", "w", encoding="utf-8") as f:
            json.dump({aid: [asdict(a) for a in alist] for aid, alist in self.analyses.items()}, f, indent=2)

    def analyze(self, analysis_id: str, agent_description: str) -> List[AgencyDimension]:
        """Score an agent across 5 agency dimensions."""
        desc_lower = agent_description.lower()
        results = []

        for dim in self.DIMENSIONS:
            score = 0.5
            internalized = False

            if dim == "goal" and ("goal" in desc_lower or "objective" in desc_lower):
                score = 0.8
                internalized = "internal" in desc_lower or "endogenous" in desc_lower
            elif dim == "identity" and ("identity" in desc_lower or "persona" in desc_lower):
                score = 0.7
                internalized = "evolv" in desc_lower or "self" in desc_lower
            elif dim == "decision_making" and ("decision" in desc_lower or "planning" in desc_lower):
                score = 0.8
                internalized = "autonomous" in desc_lower or "independent" in desc_lower
            elif dim == "self_regulation" and ("regulate" in desc_lower or "control" in desc_lower or "feedback" in desc_lower):
                score = 0.6
                internalized = "self" in desc_lower
            elif dim == "learning" and ("learn" in desc_lower or "adapt" in desc_lower):
                score = 0.7
                internalized = "self-directed" in desc_lower or "experience" in desc_lower

            results.append(AgencyDimension(
                dimension=dim, score=round(score, 2), description=f"{dim} analysis",
                is_internalized=internalized,
            ))

        self.analyses[analysis_id] = results
        self._save()
        return results

    def is_agentive(self, analysis_id: str) -> bool:
        """True agentive system has all dimensions internalized."""
        dims = self.analyses.get(analysis_id, [])
        return all(d.is_internalized for d in dims) and len(dims) == 5

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.analyses)
        agentive = sum(1 for aid in self.analyses if self.is_agentive(aid))
        return {"total_analyzed": total, "agentive": agentive, "agentic": total - agentive}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AgentCritiqueAnalyzer", "AgencyDimension"]