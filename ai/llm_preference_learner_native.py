"""LLM Preference Learner — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class PreferenceOutcome(Enum):
    PREFERRED = auto()
    REJECTED = auto()
    TIED = auto()

@dataclass
class PreferencePair:
    id: str
    option_a: str
    option_b: str
    outcome: PreferenceOutcome
    metadata: Dict[str, Any] = field(default_factory=dict)

class PreferenceLearner:
    def __init__(self) -> None:
        self._pairs: List[PreferencePair] = []
        self._scores: Dict[str, float] = {}

    def add_pair(self, pair: PreferencePair) -> None:
        self._pairs.append(pair)
        self._update_scores(pair)

    def _update_scores(self, pair: PreferencePair) -> None:
        if pair.outcome == PreferenceOutcome.PREFERRED:
            self._scores[pair.option_a] = self._scores.get(pair.option_a, 0.0) + 1.0
            self._scores[pair.option_b] = self._scores.get(pair.option_b, 0.0) - 0.5
        elif pair.outcome == PreferenceOutcome.REJECTED:
            self._scores[pair.option_a] = self._scores.get(pair.option_a, 0.0) - 0.5
            self._scores[pair.option_b] = self._scores.get(pair.option_b, 0.0) + 1.0
        else:
            self._scores[pair.option_a] = self._scores.get(pair.option_a, 0.0) + 0.1
            self._scores[pair.option_b] = self._scores.get(pair.option_b, 0.0) + 0.1

    def get_ranking(self) -> List[tuple]:
        ranked = sorted(self._scores.items(), key=lambda x: x[1], reverse=True)
        return ranked

    def get_best(self) -> Optional[str]:
        if not self._scores:
            return None
        return max(self._scores.items(), key=lambda x: x[1])[0]

    def get_stats(self) -> Dict[str, Any]:
        return {"pairs": len(self._pairs), "options": len(self._scores), "preferred": sum(1 for p in self._pairs if p.outcome == PreferenceOutcome.PREFERRED)}

def run() -> None:
    print("Preference Learner test")
    e = PreferenceLearner()
    e.add_pair(PreferencePair("p1", "model_a", "model_b", PreferenceOutcome.PREFERRED))
    e.add_pair(PreferencePair("p2", "model_b", "model_c", PreferenceOutcome.PREFERRED))
    e.add_pair(PreferencePair("p3", "model_a", "model_c", PreferenceOutcome.REJECTED))
    print("  Ranking: " + str(e.get_ranking()))
    print("  Best: " + str(e.get_best()))
    print("  Stats: " + str(e.get_stats()))
    print("Preference Learner test complete.")

if __name__ == "__main__":
    run()
