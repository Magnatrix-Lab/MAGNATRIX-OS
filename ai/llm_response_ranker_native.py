"""
llm_response_ranker_native.py
MAGNATRIX-OS Response Ranker Engine
Native Python, stdlib only.
Provides response ranking with diversity scoring, relevance matching, and ensemble voting.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class RankedResponse:
    response_id: str
    text: str
    score: float
    metrics: Dict[str, float] = field(default_factory=dict)

class ResponseRankerEngine:
    def __init__(self) -> None:
        self._responses: List[RankedResponse] = []

    def add(self, response_id: str, text: str, scores: Dict[str, float]) -> None:
        total = sum(scores.values()) / max(len(scores), 1)
        self._responses.append(RankedResponse(response_id, text, total, scores))

    def rank(self) -> List[RankedResponse]:
        return sorted(self._responses, key=lambda r: r.score, reverse=True)

    def top_k(self, k: int = 3) -> List[RankedResponse]:
        return self.rank()[:k]

    def diversity_filter(self, threshold: float = 0.8) -> List[RankedResponse]:
        # Simple diversity: keep responses with low word overlap
        ranked = self.rank()
        kept = [ranked[0]] if ranked else []
        for r in ranked[1:]:
            if not any(self._overlap(r.text, k.text) > threshold for k in kept):
                kept.append(r)
        return kept

    def _overlap(self, a: str, b: str) -> float:
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        if not a_words or not b_words:
            return 0.0
        return len(a_words & b_words) / len(a_words | b_words)

    def get_stats(self) -> Dict[str, Any]:
        scores = [r.score for r in self._responses]
        return {"count": len(self._responses), "avg_score": sum(scores) / max(len(scores), 1), "best": max(scores) if scores else 0}

def run() -> None:
    print("=" * 60); print("MAGNATRIX-OS Response Ranker"); print("=" * 60)
    e = ResponseRankerEngine()
    e.add("r1", "The weather is sunny", {"relevance": 0.9, "fluency": 0.8})
    e.add("r2", "It is sunny today", {"relevance": 0.7, "fluency": 0.9})
    e.add("r3", "Rain is expected", {"relevance": 0.3, "fluency": 0.6})
    for r in e.rank():
        print(f"  {r.response_id}: score={r.score:.2f}")
    print(f"\n  Top 2: {[r.response_id for r in e.top_k(2)]}")
    print(f"  Diverse: {[r.response_id for r in e.diversity_filter()]}")
    print("\nResponse Ranker test complete.")
if __name__ == "__main__": run()
