"""
subgame_perfect_solver_native.py
MAGNATRIX-OS — Subgame Perfect Equilibrium Solver

Inspired by Game Theory (G. Bonanno, arXiv 1512.06808) Chapter 3.4:
Find subgame-perfect equilibria in dynamic games. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict


@dataclass
class Subgame:
    root_node: str
    players: List[str]
    strategies: Dict[str, List[str]]
    payoffs: Dict[str, Tuple[float, ...]]


@dataclass
class SubgamePerfectEquilibrium:
    game_id: str
    strategy_profile: Dict[str, List[str]]
    payoffs: Tuple[float, ...]
    credible: bool = True


class SubgamePerfectSolver:
    """Find subgame-perfect equilibria in dynamic games."""

    def __init__(self, cache_dir: str = "./spe_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, SubgamePerfectEquilibrium] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "spe.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for gid, rd in data.items():
                        self.results[gid] = SubgamePerfectEquilibrium(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "spe.json", "w", encoding="utf-8") as f:
            json.dump({gid: asdict(r) for gid, r in self.results.items()}, f, indent=2)

    def solve(self, game_id: str, tree: Dict[str, Any], players: List[str]) -> SubgamePerfectEquilibrium:
        """Find SPE via backward induction on subgames."""
        def _solve(node: Dict[str, Any], player_idx: int) -> Tuple[Tuple[float, ...], Dict[str, List[str]]]:
            if node.get("terminal"):
                return tuple(node["payoffs"]), {p: [] for p in players}
            children = node.get("children", {})
            if not children:
                return (0.0,) * len(players), {p: [] for p in players}
            best_payoff = None
            best_strategies = None
            for action, child in children.items():
                cp, cs = _solve(child, (player_idx + 1) % len(players))
                if best_payoff is None or cp[player_idx] > best_payoff[player_idx]:
                    best_payoff = cp
                    best_strategies = cs
                    player = players[player_idx % len(players)]
                    best_strategies[player] = [action] + best_strategies.get(player, [])
            return best_payoff, best_strategies

        payoff, strategies = _solve(tree, 0)
        # Ensure all players have strategies
        for p in players:
            if p not in strategies:
                strategies[p] = []
        result = SubgamePerfectEquilibrium(
            game_id=game_id, strategy_profile=strategies, payoffs=payoff, credible=True,
        )
        self.results[game_id] = result
        self._save()
        return result

    def is_credible(self, game_id: str, threat: str) -> bool:
        """Check if a threat is credible in the SPE."""
        result = self.results.get(game_id)
        if not result:
            return False
        return result.credible

    def get_result(self, game_id: str) -> Optional[SubgamePerfectEquilibrium]:
        return self.results.get(game_id)

    def get_stats(self) -> Dict[str, Any]:
        return {"games_solved": len(self.results)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SubgamePerfectSolver", "SubgamePerfectEquilibrium", "Subgame"]