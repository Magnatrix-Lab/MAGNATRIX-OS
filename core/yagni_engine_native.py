"""
yagni_engine_native.py
MAGNATRIX-OS — YAGNI Engine

Inspired by Ponytail (DietrichGebert): "The best code is the code you never wrote."
YAGNI (You Ain't Gonna Need It) principle engine for code generation decisions. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class YAGNIDecision:
    decision_id: str
    feature: str
    decision: str  # "implement", "defer", "reject"
    reason: str
    estimated_loc: int
    complexity_score: float
    confidence: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class YAGNIEngine:
    """YAGNI principle engine: defer or reject unnecessary features."""

    YAGNI_RULES = [
        "Is the feature needed for the current task?",
        "Can an existing solution handle this?",
        "Will this create more maintenance burden?",
        "Is there a simpler 80/20 solution?",
        "Can this be a one-liner instead of a module?",
    ]

    def __init__(self, cache_dir: str = "./yagni_decisions"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.decisions: Dict[str, YAGNIDecision] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "decisions.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for did, dd in data.items():
                        self.decisions[did] = YAGNIDecision(**dd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "decisions.json", "w", encoding="utf-8") as f:
            json.dump({did: asdict(d) for did, d in self.decisions.items()}, f, indent=2)

    def evaluate(self, decision_id: str, feature: str, context: str,
                 estimated_loc: int = 0, complexity: float = 0.5) -> YAGNIDecision:
        """Evaluate a feature against YAGNI principles."""
        score = 0.0
        reasons = []
        if estimated_loc > 100:
            score += 0.3
            reasons.append("High LOC estimate suggests over-engineering")
        if complexity > 0.7:
            score += 0.3
            reasons.append("High complexity score")
        if "maybe" in context.lower() or "future" in context.lower() or "later" in context.lower():
            score += 0.4
            reasons.append("Future-oriented language detected - defer")
        if "reuse" in context.lower() or "existing" in context.lower():
            score -= 0.2
            reasons.append("Explicit reuse intent detected")
        if "simple" in context.lower() or "minimal" in context.lower():
            score -= 0.2

        score = max(0.0, min(1.0, score))
        if score > 0.6:
            decision = "reject"
        elif score > 0.3:
            decision = "defer"
        else:
            decision = "implement"

        result = YAGNIDecision(
            decision_id=decision_id, feature=feature, decision=decision,
            reason="; ".join(reasons) if reasons else "Passes YAGNI review",
            estimated_loc=estimated_loc, complexity_score=complexity, confidence=round(1 - score, 2),
        )
        self.decisions[decision_id] = result
        self._save()
        return result

    def get_decision(self, decision_id: str) -> Optional[YAGNIDecision]:
        return self.decisions.get(decision_id)

    def list_decisions(self, decision_type: Optional[str] = None) -> List[YAGNIDecision]:
        if decision_type:
            return [d for d in self.decisions.values() if d.decision == decision_type]
        return list(self.decisions.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.decisions)
        rejected = sum(1 for d in self.decisions.values() if d.decision == "reject")
        deferred = sum(1 for d in self.decisions.values() if d.decision == "defer")
        implemented = sum(1 for d in self.decisions.values() if d.decision == "implement")
        return {"total": total, "rejected": rejected, "deferred": deferred, "implemented": implemented}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["YAGNIEngine", "YAGNIDecision"]