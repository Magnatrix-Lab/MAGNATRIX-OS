"""
water_filling_optimizer_native.py
MAGNATRIX-OS — Water-Filling Optimizer

Inspired by NVIDIA RDKV reverse water-filling for bit allocation:
Optimal bit-width assignment via reverse water-filling over distortion weights. Pure stdlib.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict


@dataclass
class WaterLevel:
    unit_id: str
    weight: float
    allocated_bits: float


class WaterFillingOptimizer:
    """Reverse water-filling for optimal bit-width allocation."""

    def __init__(self, cache_dir: str = "./water_filling"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, List[WaterLevel]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.results[k] = [WaterLevel(**w) for w in v]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({k: [asdict(w) for w in v] for k, v in self.results.items()}, f, indent=2)

    def solve(self, problem_id: str, weights: List[Tuple[str, float]], total_budget: int,
              bit_set: List[int] = None) -> List[WaterLevel]:
        """Reverse water-filling: allocate bits to minimize weighted distortion."""
        if bit_set is None:
            bit_set = [0, 2, 4, 8, 16]
        if not weights or total_budget <= 0:
            return []

        # Continuous relaxation: bu = log2(wu * sigma / lambda)+
        # For simplicity, use sigma = 1 and compute lambda from budget constraint
        sorted_weights = sorted(weights, key=lambda x: x[1], reverse=True)

        # Binary search for lambda
        lo, hi = 0.0001, max(w for _, w in weights) * 2
        for _ in range(50):
            mid = (lo + hi) / 2
            total_bits = sum(max(0, math.log2(w / mid)) for _, w in weights if w > mid)
            if total_bits > total_budget:
                lo = mid
            else:
                hi = mid
        lambda_opt = (lo + hi) / 2

        levels = []
        for unit_id, weight in sorted_weights:
            bits = max(0.0, math.log2(weight / lambda_opt)) if weight > lambda_opt else 0.0
            # Snap to nearest supported bit-width
            snapped = min(bit_set, key=lambda b: abs(b - bits))
            levels.append(WaterLevel(unit_id, weight, round(snapped, 2)))

        self.results[problem_id] = levels
        self._save()
        return levels

    def get_result(self, problem_id: str) -> List[WaterLevel]:
        return self.results.get(problem_id, [])

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(v) for v in self.results.values())
        return {"problems_solved": len(self.results), "total_levels": total}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["WaterFillingOptimizer", "WaterLevel"]