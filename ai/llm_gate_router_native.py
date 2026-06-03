"""
llm_gate_router_native.py
MAGNATRIX-OS Gate Router Engine
Native Python, stdlib only.
Provides expert gate routing, top-k selection, score normalization, and bias routing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class GateRouterEngine:
    """Expert gate routing with top-k selection."""

    def __init__(self, top_k: int = 2, score_func: str = "softmax") -> None:
        self.top_k = top_k
        self.score_func = score_func

    def route(self, scores: List[float]) -> List[Tuple[int, float]]:
        indexed = [(i, s) for i, s in enumerate(scores)]
        indexed.sort(key=lambda x: x[1], reverse=True)
        top = indexed[:self.top_k]

        if self.score_func == "softmax":
            max_s = max(s for _, s in top)
            exp = [math.exp(s - max_s) for _, s in top]
            total = sum(exp)
            weights = [(i, e / total) for (i, _), e in zip(top, exp)]
        elif self.score_func == "sigmoid":
            sig = [1.0 / (1.0 + math.exp(-s)) for _, s in top]
            total = sum(sig)
            weights = [(i, s / total) for (i, _), s in zip(top, sig)]
        else:
            weights = top
        return weights

    def get_stats(self) -> Dict[str, Any]:
        return {"top_k": self.top_k, "score_func": self.score_func}


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Gate Router Engine")
    print("=" * 60)
    engine = GateRouterEngine(top_k=3, score_func="softmax")
    scores = [0.2, 0.8, 0.5, 0.1, 0.9, 0.3]
    result = engine.route(scores)
    print(f"  Scores: {scores}")
    print(f"  Top-{engine.top_k}: {result}")
    print("\nGate Router test complete.")

if __name__ == "__main__":
    run()
