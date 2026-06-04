"""Hyperparameter Search - Grid/random search for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any
from enum import Enum, auto
import random

class SearchType(Enum):
    GRID = auto(); RANDOM = auto()

@dataclass
class HyperparameterSearch:
    search_type: SearchType = SearchType.GRID
    param_space: Dict[str, List[Any]] = field(default_factory=dict)
    best_params: Dict[str, Any] = field(default_factory=dict)
    best_score: float = float('-inf')

    def search(self, evaluator: callable, n_trials: int = 10) -> Dict[str, Any]:
        if self.search_type == SearchType.GRID:
            keys = list(self.param_space.keys())
            from itertools import product
            for values in product(*[self.param_space[k] for k in keys]):
                params = dict(zip(keys, values))
                score = evaluator(params)
                if score > self.best_score: self.best_score = score; self.best_params = params
        else:
            for _ in range(n_trials):
                params = {k: random.choice(v) for k, v in self.param_space.items()}
                score = evaluator(params)
                if score > self.best_score: self.best_score = score; self.best_params = params
        return self.best_params

    def stats(self) -> dict:
        return {"search": self.search_type.name, "best_score": round(self.best_score, 4), "best": self.best_params}

def run():
    hs = HyperparameterSearch(SearchType.GRID, {"lr": [0.01, 0.1], "batch": [16, 32]})
    best = hs.search(lambda p: p["lr"] * 100 - p["batch"])
    print("Best:", best)
    print("Stats:", hs.stats())

if __name__ == "__main__": run()
