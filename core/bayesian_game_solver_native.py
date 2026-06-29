"""
bayesian_game_solver_native.py
MAGNATRIX-OS — Bayesian Game Solver

Inspired by Game Theory (G. Bonanno, arXiv 1512.06808) Chapter 13-15:
Solve games with incomplete information using Bayesian Nash equilibrium. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict


@dataclass
class BayesianPlayer:
    player_id: str
    types: List[str]
    type_probabilities: Dict[str, float]
    strategies: List[str]


@dataclass
class BayesianEquilibrium:
    game_id: str
    strategy_map: Dict[str, Dict[str, str]]  # player -> type -> strategy
    expected_payoffs: Dict[str, float]


class BayesianGameSolver:
    """Solve Bayesian games with incomplete information."""

    def __init__(self, cache_dir: str = "./bayesian_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, BayesianEquilibrium] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "bayesian.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for gid, rd in data.items():
                        self.results[gid] = BayesianEquilibrium(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "bayesian.json", "w", encoding="utf-8") as f:
            json.dump({gid: asdict(r) for gid, r in self.results.items()}, f, indent=2)

    def solve(self, game_id: str, players: List[BayesianPlayer],
              payoff_matrix: Dict[str, Dict[str, Dict[str, Dict[str, float]]]]) -> BayesianEquilibrium:
        """Find Bayesian Nash equilibrium for simple 2-player games."""
        strategy_map = {}
        expected_payoffs = {}
        for p in players:
            strategy_map[p.player_id] = {}
            for t in p.types:
                # Simple heuristic: choose strategy that maximizes expected payoff given type
                best_s, best_exp = None, float('-inf')
                for s in p.strategies:
                    exp = 0.0
                    for other in players:
                        if other.player_id == p.player_id:
                            continue
                        for ot in other.types:
                            prob = other.type_probabilities.get(ot, 1.0 / len(other.types))
                            # Expected payoff against other's strategy
                            opp_s = strategy_map.get(other.player_id, {}).get(ot, other.strategies[0])
                            key = f"{p.player_id}_{t}_{s}_vs_{other.player_id}_{ot}_{opp_s}"
                            payoff = self._lookup_payoff(payoff_matrix, p.player_id, t, s, other.player_id, ot, opp_s)
                            exp += prob * payoff
                    if exp > best_exp:
                        best_exp = exp
                        best_s = s
                strategy_map[p.player_id][t] = best_s or p.strategies[0]
                expected_payoffs[f"{p.player_id}_{t}"] = round(best_exp, 4)
        result = BayesianEquilibrium(game_id, strategy_map, expected_payoffs)
        self.results[game_id] = result
        self._save()
        return result

    def _lookup_payoff(self, matrix, p1, t1, s1, p2, t2, s2):
        try:
            return matrix[p1][t1][s1][f"{p2}_{t2}_{s2}"]
        except (KeyError, TypeError):
            return 0.0

    def get_result(self, game_id: str) -> Optional[BayesianEquilibrium]:
        return self.results.get(game_id)

    def get_stats(self) -> Dict[str, Any]:
        return {"games_solved": len(self.results)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["BayesianGameSolver", "BayesianPlayer", "BayesianEquilibrium"]