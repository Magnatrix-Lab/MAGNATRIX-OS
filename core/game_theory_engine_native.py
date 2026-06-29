"""
game_theory_engine_native.py
MAGNATRIX-OS — Game Theory Engine

Inspired by Game Theory (G. Bonanno, arXiv 1512.06808):
Core game theory primitives: normal form, extensive form, payoff matrices, strategy sets. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum, auto


class GameType(Enum):
    NORMAL_FORM = auto()
    EXTENSIVE_FORM = auto()
    COOPERATIVE = auto()
    BAYESIAN = auto()


@dataclass
class Player:
    player_id: str
    name: str
    strategies: List[str] = field(default_factory=list)
    payoff_function: Optional[Dict[str, Any]] = None


@dataclass
class GameOutcome:
    strategy_profile: Tuple[str, ...]
    payoffs: Tuple[float, ...]
    is_nash: bool = False
    is_pareto_optimal: bool = False


class GameTheoryEngine:
    """Core game theory primitives for normal and extensive form games."""

    def __init__(self, games_dir: str = "./games"):
        self.games_dir = Path(games_dir)
        self.games_dir.mkdir(exist_ok=True)
        self.games: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        file = self.games_dir / "games.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self.games = json.load(f)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.games_dir / "games.json", "w", encoding="utf-8") as f:
            json.dump(self.games, f, indent=2)

    def create_normal_form(self, game_id: str, players: List[str],
                           strategies: List[List[str]], payoff_matrix: List[List[Tuple[float, ...]]]) -> Dict[str, Any]:
        game = {
            "game_id": game_id, "type": "normal_form", "players": players,
            "strategies": strategies, "payoff_matrix": payoff_matrix,
        }
        self.games[game_id] = game
        self._save()
        return game

    def create_extensive_form(self, game_id: str, players: List[str], tree: Dict[str, Any]) -> Dict[str, Any]:
        game = {
            "game_id": game_id, "type": "extensive_form", "players": players, "tree": tree,
        }
        self.games[game_id] = game
        self._save()
        return game

    def get_payoff(self, game_id: str, profile: Tuple[str, ...]) -> Optional[Tuple[float, ...]]:
        game = self.games.get(game_id)
        if not game or game["type"] != "normal_form":
            return None
        matrix = game["payoff_matrix"]
        strategies = game["strategies"]
        try:
            idx = tuple(s.index(p) for s, p in zip(strategies, profile))
            return tuple(matrix[idx[0]][idx[1]]) if len(idx) == 2 else None
        except ValueError:
            return None

    def get_all_profiles(self, game_id: str) -> List[Tuple[str, ...]]:
        game = self.games.get(game_id)
        if not game:
            return []
        from itertools import product
        return list(product(*game["strategies"]))

    def delete_game(self, game_id: str) -> bool:
        if game_id in self.games:
            del self.games[game_id]
            self._save()
            return True
        return False

    def get_game(self, game_id: str) -> Optional[Dict[str, Any]]:
        return self.games.get(game_id)

    def list_games(self) -> List[str]:
        return list(self.games.keys())

    def get_stats(self) -> Dict[str, Any]:
        types = {}
        for g in self.games.values():
            t = g.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        return {"total_games": len(self.games), "types": types}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["GameTheoryEngine", "Player", "GameOutcome", "GameType"]