"""
mixed_strategy_calculator_native.py
MAGNATRIX-OS — Mixed Strategy Calculator

Inspired by Game Theory (G. Bonanno, arXiv 1512.06808) Chapter 5:
Compute mixed strategy Nash equilibria for 2x2 and general games. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
import random


@dataclass
class MixedStrategy:
    player_id: str
    probabilities: Dict[str, float]
    expected_payoff: float = 0.0


class MixedStrategyCalculator:
    """Compute mixed strategy Nash equilibria for 2-player games."""

    def __init__(self, cache_dir: str = "./mixed_strategy_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "mixed.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "mixed.json", "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2)

    def solve_2x2(self, game_id: str, payoff_p1: List[List[float]], payoff_p2: List[List[float]],
                  s1: List[str], s2: List[str]) -> Tuple[MixedStrategy, MixedStrategy]:
        """Solve mixed strategy for 2x2 game."""
        a, b = payoff_p1[0][0], payoff_p1[0][1]
        c, d = payoff_p1[1][0], payoff_p1[1][1]
        e, f = payoff_p2[0][0], payoff_p2[0][1]
        g, h = payoff_p2[1][0], payoff_p2[1][1]

        denom1 = (a - c) + (d - b)
        if denom1 == 0:
            p = 0.5
        else:
            p = (d - c) / denom1
        p = max(0.0, min(1.0, p))

        denom2 = (e - g) + (h - f)
        if denom2 == 0:
            q = 0.5
        else:
            q = (h - g) / denom2
        q = max(0.0, min(1.0, q))

        m1 = MixedStrategy("P1", {s1[0]: round(q, 4), s1[1]: round(1 - q, 4)})
        m2 = MixedStrategy("P2", {s2[0]: round(p, 4), s2[1]: round(1 - p, 4)})

        m1.expected_payoff = round(q * (a * p + b * (1 - p)) + (1 - q) * (c * p + d * (1 - p)), 4)
        m2.expected_payoff = round(p * (e * q + g * (1 - q)) + (1 - p) * (f * q + h * (1 - q)), 4)

        self.cache[game_id] = {"p1": asdict(m1), "p2": asdict(m2)}
        self._save()
        return m1, m2

    def expected_payoff(self, payoff_matrix: List[List[float]],
                        mixed1: Dict[str, float], mixed2: Dict[str, float],
                        strategies1: List[str], strategies2: List[str]) -> float:
        exp = 0.0
        for i, s1 in enumerate(strategies1):
            for j, s2 in enumerate(strategies2):
                exp += mixed1.get(s1, 0) * mixed2.get(s2, 0) * payoff_matrix[i][j]
        return round(exp, 4)

    def get_stats(self) -> Dict[str, Any]:
        return {"games_solved": len(self.cache)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MixedStrategyCalculator", "MixedStrategy"]