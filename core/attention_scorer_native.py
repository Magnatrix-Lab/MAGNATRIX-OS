"""
attention_scorer_native.py
MAGNATRIX-OS — Attention Scorer

Inspired by NVIDIA KV-cache compression (token importance from attention weights):
Score token importance from attention distributions and query/key column norms. Pure stdlib.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class TokenScore:
    token_id: int
    attention_weight: float
    importance_score: float
    layer: int
    head: int


class AttentionScorer:
    """Score token importance from attention weights and Q/K norms."""

    def __init__(self, cache_dir: str = "./attention_scores"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.scores: Dict[str, List[TokenScore]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "scores.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.scores[k] = [TokenScore(**s) for s in v]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "scores.json", "w", encoding="utf-8") as f:
            json.dump({k: [asdict(s) for s in v] for k, v in self.scores.items()}, f, indent=2)

    def score_by_attention(self, attention_weights: List[List[float]], layer: int, head: int) -> List[TokenScore]:
        """Score tokens by accumulated attention weight across queries."""
        num_tokens = len(attention_weights[0]) if attention_weights else 0
        scores = []
        for t in range(num_tokens):
            w = sum(row[t] for row in attention_weights) / max(len(attention_weights), 1)
            scores.append(TokenScore(
                token_id=t, attention_weight=round(w, 6),
                importance_score=round(w, 6), layer=layer, head=head,
            ))
        key = f"{layer}_{head}"
        self.scores[key] = scores
        self._save()
        return scores

    def score_by_qk_norms(self, query_matrix: List[List[float]], key_matrix: List[List[float]],
                           layer: int, head: int) -> List[TokenScore]:
        """Score channels by Q/K column norm product (ThinK-style)."""
        if not query_matrix or not key_matrix:
            return []
        d = len(query_matrix[0])
        scores = []
        for c in range(d):
            q_norm = math.sqrt(sum(row[c] ** 2 for row in query_matrix))
            k_norm = math.sqrt(sum(row[c] ** 2 for row in key_matrix))
            score = q_norm * k_norm / math.sqrt(d)
            scores.append(TokenScore(
                token_id=c, attention_weight=0.0,
                importance_score=round(score, 6), layer=layer, head=head,
            ))
        key = f"{layer}_{head}_channels"
        self.scores[key] = scores
        self._save()
        return scores

    def top_k(self, layer: int, head: int, k: int) -> List[TokenScore]:
        key = f"{layer}_{head}"
        scores = self.scores.get(key, [])
        return sorted(scores, key=lambda x: x.importance_score, reverse=True)[:k]

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(v) for v in self.scores.values())
        return {"total_scores": total, "heads_scored": len(self.scores)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AttentionScorer", "TokenScore"]