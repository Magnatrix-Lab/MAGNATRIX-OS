"""
cache_eviction_engine_native.py
MAGNATRIX-OS — Cache Eviction Engine

Inspired by NVIDIA KV-cache compression (H2O, SnapKV, StreamingLLM):
Token eviction strategies for KV cache compression. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class EvictionPlan:
    layer: int
    head: int
    keep_tokens: List[int]
    evict_tokens: List[int]
    strategy: str


class CacheEvictionEngine:
    """Token eviction strategies for KV cache compression."""

    STRATEGIES = {
        "h2o": "Heavy-Hitter Oracle - keep top attention tokens",
        "snapkv": "SnapKV - attention scoring with observation window",
        "streaming": "StreamingLLM - sink tokens + recent window",
        "recent_only": "Keep only recent N tokens",
        "random": "Random eviction",
    }

    def __init__(self, plans_dir: str = "./eviction_plans"):
        self.plans_dir = Path(plans_dir)
        self.plans_dir.mkdir(exist_ok=True)
        self.plans: Dict[str, EvictionPlan] = {}
        self._load()

    def _load(self) -> None:
        file = self.plans_dir / "plans.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, pd in data.items():
                        self.plans[pid] = EvictionPlan(**pd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.plans_dir / "plans.json", "w", encoding="utf-8") as f:
            json.dump({pid: asdict(p) for pid, p in self.plans.items()}, f, indent=2)

    def h2o_evict(self, token_scores: List[float], budget: int, layer: int, head: int) -> EvictionPlan:
        """H2O: Keep top-K tokens by accumulated attention score."""
        indexed = list(enumerate(token_scores))
        top = sorted(indexed, key=lambda x: x[1], reverse=True)[:budget]
        keep = sorted([i for i, _ in top])
        all_tokens = list(range(len(token_scores)))
        evict = [t for t in all_tokens if t not in keep]
        plan = EvictionPlan(layer=layer, head=head, keep_tokens=keep, evict_tokens=evict, strategy="h2o")
        self.plans[f"h2o_{layer}_{head}"] = plan
        self._save()
        return plan

    def streaming_evict(self, seq_len: int, sink_tokens: int, recent_window: int, layer: int, head: int) -> EvictionPlan:
        """StreamingLLM: Keep sink tokens + recent window."""
        keep = list(range(sink_tokens)) + list(range(max(sink_tokens, seq_len - recent_window), seq_len))
        keep = sorted(set(keep))
        evict = [t for t in range(seq_len) if t not in keep]
        plan = EvictionPlan(layer=layer, head=head, keep_tokens=keep, evict_tokens=evict, strategy="streaming")
        self.plans[f"streaming_{layer}_{head}"] = plan
        self._save()
        return plan

    def recent_window_evict(self, seq_len: int, window: int, layer: int, head: int) -> EvictionPlan:
        """Keep only the most recent N tokens."""
        keep = list(range(max(0, seq_len - window), seq_len))
        evict = [t for t in range(seq_len) if t not in keep]
        plan = EvictionPlan(layer=layer, head=head, keep_tokens=keep, evict_tokens=evict, strategy="recent_only")
        self.plans[f"recent_{layer}_{head}"] = plan
        self._save()
        return plan

    def get_plan(self, plan_id: str) -> Optional[EvictionPlan]:
        return self.plans.get(plan_id)

    def get_stats(self) -> Dict[str, Any]:
        total_evicted = sum(len(p.evict_tokens) for p in self.plans.values())
        total_kept = sum(len(p.keep_tokens) for p in self.plans.values())
        return {"total_plans": len(self.plans), "total_evicted": total_evicted, "total_kept": total_kept}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CacheEvictionEngine", "EvictionPlan"]