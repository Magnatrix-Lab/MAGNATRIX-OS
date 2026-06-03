"""
llm_ensemble_voter_native.py
MAGNATRIX-OS Ensemble Voter Engine
Native Python, stdlib only.
Provides ensemble voting with weighted majority, confidence aggregation, and disagreement detection.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class Vote:
    voter_id: str
    choice: str
    confidence: float = 1.0

class EnsembleVoterEngine:
    def __init__(self) -> None:
        self._votes: List[Vote] = []
        self._weights: Dict[str, float] = {}

    def set_weight(self, voter_id: str, weight: float) -> None:
        self._weights[voter_id] = weight

    def vote(self, voter_id: str, choice: str, confidence: float = 1.0) -> None:
        self._votes.append(Vote(voter_id, choice, confidence))

    def tally(self) -> Dict[str, Any]:
        scores: Dict[str, float] = {}
        for v in self._votes:
            w = self._weights.get(v.voter_id, 1.0) * v.confidence
            scores[v.choice] = scores.get(v.choice, 0.0) + w
        if not scores:
            return {"winner": None, "scores": {}}
        winner = max(scores, key=scores.get)
        return {"winner": winner, "scores": scores, "total_votes": len(self._votes), "agreement": max(scores.values()) / sum(scores.values())}

    def get_disagreement(self) -> float:
        if len(self._votes) < 2:
            return 0.0
        unique = len(set(v.choice for v in self._votes))
        return unique / len(self._votes)

    def reset(self) -> None:
        self._votes.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {"votes": len(self._votes), "weights": len(self._weights)}

def run() -> None:
    print("=" * 60); print("MAGNATRIX-OS Ensemble Voter"); print("=" * 60)
    e = EnsembleVoterEngine()
    e.set_weight("model_a", 2.0)
    e.set_weight("model_b", 1.0)
    e.set_weight("model_c", 1.0)
    e.vote("model_a", "positive", 0.9)
    e.vote("model_b", "positive", 0.7)
    e.vote("model_c", "negative", 0.6)
    print(f"  Tally: {e.tally()}")
    print(f"  Disagreement: {e.get_disagreement():.2f}")
    print("\nEnsemble Voter test complete.")
if __name__ == "__main__": run()
