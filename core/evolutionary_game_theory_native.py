"""
evolutionary_game_theory_native.py
MAGNATRIX-OS — Evolutionary Game Theory

Inspired by Game Theory (G. Bonanno, arXiv 1512.06808) evolutionary dynamics:
Replicator dynamics, ESS, and population game analysis. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class PopulationState:
    strategies: Dict[str, float]
    payoffs: Dict[str, float] = field(default_factory=dict)
    avg_payoff: float = 0.0


class EvolutionaryGameTheory:
    """Evolutionary game theory: replicator dynamics and ESS."""

    def __init__(self, cache_dir: str = "./evolutionary_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.history: List[PopulationState] = []
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "history.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = [PopulationState(**d) for d in data]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "history.json", "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in self.history], f, indent=2)

    def replicator_dynamics(self, payoff_matrix: List[List[float]],
                            strategies: List[str], initial_state: Dict[str, float],
                            generations: int = 100) -> List[PopulationState]:
        """Simulate replicator dynamics over generations."""
        state = PopulationState(strategies={s: initial_state.get(s, 1.0 / len(strategies)) for s in strategies})
        history = []
        for gen in range(generations):
            payoffs = {}
            for i, s in enumerate(strategies):
                exp = 0.0
                for j, s2 in enumerate(strategies):
                    exp += state.strategies[s2] * payoff_matrix[i][j]
                payoffs[s] = round(exp, 4)
            avg = sum(state.strategies[s] * payoffs[s] for s in strategies)
            new_strategies = {}
            for s in strategies:
                new_strategies[s] = max(0.0, state.strategies[s] * (payoffs[s] - avg) + state.strategies[s])
            total = sum(new_strategies.values())
            if total > 0:
                new_strategies = {s: round(v / total, 6) for s, v in new_strategies.items()}
            state = PopulationState(strategies=new_strategies, payoffs=payoffs, avg_payoff=round(avg, 4))
            history.append(state)
        self.history = history
        self._save()
        return history

    def is_ess(self, payoff_matrix: List[List[float]], strategies: List[str],
               candidate: str) -> bool:
        """Check if a strategy is an Evolutionarily Stable Strategy."""
        try:
            i = strategies.index(candidate)
        except ValueError:
            return False
        for j, other in enumerate(strategies):
            if other == candidate:
                continue
            if payoff_matrix[i][j] > payoff_matrix[j][j]:
                continue
            if payoff_matrix[i][j] == payoff_matrix[j][j] and payoff_matrix[i][i] > payoff_matrix[j][i]:
                continue
            return False
        return True

    def find_ess(self, payoff_matrix: List[List[float]], strategies: List[str]) -> List[str]:
        return [s for s in strategies if self.is_ess(payoff_matrix, strategies, s)]

    def get_stats(self) -> Dict[str, Any]:
        return {"generations_simulated": len(self.history)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["EvolutionaryGameTheory", "PopulationState"]