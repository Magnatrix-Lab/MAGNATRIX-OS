"""
nash_equilibrium_solver_native.py
MAGNATRIX-OS — Nash Equilibrium Solver

Inspired by Game Theory (G. Bonanno, arXiv 1512.06808) Chapter 1.6:
Find pure and mixed strategy Nash equilibria in strategic-form games. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict


@dataclass
class NashEquilibrium:
    game_id: str
    strategy_profile: Tuple[str, ...]
    payoffs: Tuple[float, ...]
    is_pure: bool = True
    equilibrium_type: str = "nash"


class NashEquilibriumSolver:
    """Find Nash equilibria in strategic-form games."""

    def __init__(self, cache_dir: str = "./nash_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, List[NashEquilibrium]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for gid, elist in data.items():
                        self.results[gid] = [NashEquilibrium(**e) for e in elist]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({gid: [asdict(e) for e in elist] for gid, elist in self.results.items()}, f, indent=2)

    def find_pure_nash(self, game_id: str, payoff_matrix: List[List[Tuple[float, ...]]],
                        strategies: List[List[str]], players: List[str]) -> List[NashEquilibrium]:
        equilibria = []
        from itertools import product
        profiles = list(product(*strategies))
        for profile in profiles:
            payoffs = self._get_payoff(payoff_matrix, strategies, profile)
            if payoffs is None:
                continue
            is_nash = self._check_nash(payoff_matrix, strategies, profile, payoffs)
            if is_nash:
                equilibria.append(NashEquilibrium(game_id, profile, payoffs, is_pure=True))
        self.results[game_id] = equilibria
        self._save()
        return equilibria

    def _get_payoff(self, matrix, strategies, profile):
        try:
            idx = tuple(s.index(p) for s, p in zip(strategies, profile))
            return tuple(matrix[idx[0]][idx[1]]) if len(idx) == 2 else None
        except ValueError:
            return None

    def _check_nash(self, matrix, strategies, profile, payoffs):
        idx = tuple(s.index(p) for s, p in zip(strategies, profile))
        for player in range(len(strategies)):
            for alt in range(len(strategies[player])):
                if alt == idx[player]:
                    continue
                alt_idx = list(idx)
                alt_idx[player] = alt
                alt_payoffs = tuple(matrix[alt_idx[0]][alt_idx[1]]) if len(alt_idx) == 2 else None
                if alt_payoffs and alt_payoffs[player] > payoffs[player]:
                    return False
        return True

    def dominant_strategies(self, payoff_matrix: List[List[Tuple[float, ...]]],
                             strategies: List[List[str]]) -> Dict[str, str]:
        result = {}
        for player in range(len(strategies)):
            best = None
            best_payoff = float('-inf')
            for s in range(len(strategies[player])):
                min_payoff = float('inf')
                for opp in range(len(strategies[1 - player])):
                    idx = (s, opp) if player == 0 else (opp, s)
                    p = payoff_matrix[idx[0]][idx[1]][player]
                    min_payoff = min(min_payoff, p)
                if min_payoff > best_payoff:
                    best_payoff = min_payoff
                    best = strategies[player][s]
            if best:
                result[strategies[player][s]] = best
        return result

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(e) for e in self.results.values())
        return {"total_equilibria": total, "games_analyzed": len(self.results)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["NashEquilibriumSolver", "NashEquilibrium"]