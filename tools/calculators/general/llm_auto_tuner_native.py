"""Auto-Tuner — hyperparameter optimization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable, Any
from enum import Enum, auto
import random
import math
import time

class SearchStrategy(Enum):
    GRID = auto()
    RANDOM = auto()
    BAYESIAN = auto()
    EVOLUTIONARY = auto()

@dataclass
class Hyperparameter:
    name: str
    param_type: str
    range: Tuple[float, float]
    log_scale: bool = False

@dataclass
class TuningResult:
    config: Dict[str, Any]
    score: float
    trial_id: int

class AutoTuner:
    def __init__(self, strategy: SearchStrategy = SearchStrategy.RANDOM, max_trials: int = 100):
        self.strategy = strategy
        self.max_trials = max_trials
        self.hyperparameters: List[Hyperparameter] = []
        self.results: List[TuningResult] = []
        self.best_result: Optional[TuningResult] = None

    def add_hyperparameter(self, name: str, param_type: str, range_vals: Tuple[float, float], log_scale: bool = False):
        self.hyperparameters.append(Hyperparameter(name, param_type, range_vals, log_scale))

    def _sample(self, hp: Hyperparameter) -> Any:
        lo, hi = hp.range
        if hp.log_scale:
            lo, hi = math.log(lo), math.log(hi)
            val = random.uniform(lo, hi)
            val = math.exp(val)
        else:
            val = random.uniform(lo, hi)
        if hp.param_type == "int":
            return int(val)
        elif hp.param_type == "float":
            return val
        elif hp.param_type == "choice":
            return random.choice(list(range(int(lo), int(hi) + 1)))
        return val

    def _sample_config(self) -> Dict[str, Any]:
        return {hp.name: self._sample(hp) for hp in self.hyperparameters}

    def tune(self, objective: Callable[[Dict[str, Any]], float]) -> TuningResult:
        for trial in range(self.max_trials):
            config = self._sample_config()
            try:
                score = objective(config)
            except Exception as e:
                score = float('inf')
            result = TuningResult(config, score, trial)
            self.results.append(result)
            if self.best_result is None or score < self.best_result.score:
                self.best_result = result
        return self.best_result

    def get_top_k(self, k: int = 5) -> List[TuningResult]:
        return sorted(self.results, key=lambda r: r.score)[:k]

    def stats(self) -> Dict:
        return {"trials": len(self.results), "best_score": self.best_result.score if self.best_result else None, "strategy": self.strategy.name}

def run():
    tuner = AutoTuner(SearchStrategy.RANDOM, 50)
    tuner.add_hyperparameter("lr", "float", (0.001, 0.1))
    tuner.add_hyperparameter("batch_size", "int", (16, 128))
    def objective(config):
        return (config["lr"] - 0.01) ** 2 + (config["batch_size"] - 64) ** 2
    best = tuner.tune(objective)
    print("Best:", best.config, best.score)
    print(tuner.stats())

if __name__ == "__main__":
    run()
