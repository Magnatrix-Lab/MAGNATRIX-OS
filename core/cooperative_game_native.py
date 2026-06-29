"""
cooperative_game_native.py
MAGNATRIX-OS — Cooperative Game Theory

Inspired by Game Theory (G. Bonanno, arXiv 1512.06808) cooperative games:
Coalition formation, Shapley value, and core computation. Pure stdlib.
"""

import json
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field, asdict


@dataclass
class Coalition:
    members: Set[str]
    value: float


class CooperativeGame:
    """Cooperative game theory: coalition formation, Shapley value, core."""

    def __init__(self, games_dir: str = "./cooperative_games"):
        self.games_dir = Path(games_dir)
        self.games_dir.mkdir(exist_ok=True)
        self.games: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        file = self.games_dir / "cooperative.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self.games = json.load(f)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.games_dir / "cooperative.json", "w", encoding="utf-8") as f:
            json.dump(self.games, f, indent=2)

    def create_game(self, game_id: str, players: List[str], characteristic_function: Dict[str, float]) -> Dict[str, Any]:
        game = {"game_id": game_id, "players": players, "characteristic": characteristic_function}
        self.games[game_id] = game
        self._save()
        return game

    def shapley_value(self, game_id: str) -> Dict[str, float]:
        """Compute Shapley value for each player."""
        game = self.games.get(game_id)
        if not game:
            return {}
        players = game["players"]
        cf = game["characteristic"]
        n = len(players)
        shapley = {p: 0.0 for p in players}
        from math import factorial
        for p in players:
            others = [o for o in players if o != p]
            for r in range(len(others) + 1):
                for coalition in combinations(others, r):
                    coalition_key = ",".join(sorted(coalition))
                    with_p_key = ",".join(sorted(coalition + (p,)))
                    v_without = cf.get(coalition_key, 0.0)
                    v_with = cf.get(with_p_key, 0.0)
                    weight = factorial(r) * factorial(n - r - 1) / factorial(n)
                    shapley[p] += weight * (v_with - v_without)
        return {p: round(v, 4) for p, v in shapley.items()}

    def is_in_core(self, game_id: str, allocation: Dict[str, float]) -> bool:
        """Check if allocation is in the core."""
        game = self.games.get(game_id)
        if not game:
            return False
        cf = game["characteristic"]
        players = game["players"]
        total = sum(allocation.values())
        grand_value = cf.get(",".join(sorted(players)), 0.0)
        if abs(total - grand_value) > 0.01:
            return False
        for r in range(1, len(players) + 1):
            for coalition in combinations(players, r):
                coalition_key = ",".join(sorted(coalition))
                coalition_value = cf.get(coalition_key, 0.0)
                coalition_sum = sum(allocation.get(p, 0) for p in coalition)
                if coalition_sum < coalition_value - 0.01:
                    return False
        return True

    def get_stats(self) -> Dict[str, Any]:
        return {"games": len(self.games)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CooperativeGame", "Coalition"]