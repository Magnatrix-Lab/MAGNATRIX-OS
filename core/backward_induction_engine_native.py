"""
backward_induction_engine_native.py
MAGNATRIX-OS — Backward Induction Engine

Inspired by Game Theory (G. Bonanno, arXiv 1512.06808) Chapter 2.2:
Solve extensive-form games with perfect information via backward induction. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict


@dataclass
class GameNode:
    node_id: str
    player: Optional[str]  # None for terminal
    children: Dict[str, "GameNode"] = field(default_factory=dict)
    payoffs: Optional[Tuple[float, ...]] = None
    is_terminal: bool = False
    best_action: Optional[str] = None


@dataclass
class BackwardInductionResult:
    game_id: str
    optimal_path: List[str]
    payoffs: Tuple[float, ...]
    strategy_profile: Dict[str, str]


class BackwardInductionEngine:
    """Solve extensive-form games with perfect information via backward induction."""

    def __init__(self, cache_dir: str = "./backward_induction"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, BackwardInductionResult] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for gid, rd in data.items():
                        self.results[gid] = BackwardInductionResult(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({gid: asdict(r) for gid, r in self.results.items()}, f, indent=2)

    def solve(self, game_id: str, root: Dict[str, Any], players: List[str]) -> BackwardInductionResult:
        """Solve a game tree via backward induction."""
        def _solve_node(node: Dict[str, Any], player_idx: int) -> Tuple[Tuple[float, ...], Optional[str]]:
            if node.get("terminal"):
                return tuple(node["payoffs"]), None
            children = node.get("children", {})
            if not children:
                return (0.0,) * len(players), None
            best_payoff = None
            best_action = None
            for action, child in children.items():
                cp, _ = _solve_node(child, (player_idx + 1) % len(players))
                if best_payoff is None or cp[player_idx] > best_payoff[player_idx]:
                    best_payoff = cp
                    best_action = action
            return best_payoff, best_action

        payoff, action = _solve_node(root, 0)
        # Build strategy profile
        profile = {}
        def _build_strategy(node: Dict[str, Any], player_idx: int) -> None:
            if node.get("terminal") or not node.get("children"):
                return
            _, best_action = _solve_node(node, player_idx)
            if best_action:
                player = players[player_idx % len(players)]
                profile[player] = best_action
                _build_strategy(node["children"][best_action], (player_idx + 1) % len(players))
        _build_strategy(root, 0)

        result = BackwardInductionResult(
            game_id=game_id, optimal_path=list(profile.values()),
            payoffs=payoff, strategy_profile=profile,
        )
        self.results[game_id] = result
        self._save()
        return result

    def get_result(self, game_id: str) -> Optional[BackwardInductionResult]:
        return self.results.get(game_id)

    def get_stats(self) -> Dict[str, Any]:
        return {"games_solved": len(self.results)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["BackwardInductionEngine", "GameNode", "BackwardInductionResult"]