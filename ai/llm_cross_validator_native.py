"""LLM Cross Validator — Native Python (stdlib only)."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class CrossValidator:
    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    def k_fold(self, data: List[Any], labels: List[Any], k: int, train_fn: Callable, eval_fn: Callable) -> List[float]:
        shuffled = list(zip(data, labels))
        self._rng.shuffle(shuffled)
        fold_size = len(shuffled) // k
        scores = []
        for i in range(k):
            start = i * fold_size
            end = (i + 1) * fold_size if i < k - 1 else len(shuffled)
            test = shuffled[start:end]
            train = shuffled[:start] + shuffled[end:]
            model = train_fn([x for x, _ in train], [y for _, y in train])
            score = eval_fn(model, [x for x, _ in test], [y for _, y in test])
            scores.append(score)
        return scores

    def leave_one_out(self, data: List[Any], labels: List[Any], train_fn: Callable, eval_fn: Callable) -> List[float]:
        scores = []
        for i in range(len(data)):
            train_x = data[:i] + data[i+1:]
            train_y = labels[:i] + labels[i+1:]
            model = train_fn(train_x, train_y)
            score = eval_fn(model, [data[i]], [labels[i]])
            scores.append(score)
        return scores

    def get_stats(self, scores: List[float]) -> Dict[str, Any]:
        return {"scores": scores, "mean": sum(scores) / len(scores) if scores else 0, "std": (sum((s - sum(scores) / len(scores)) ** 2 for s in scores) / len(scores)) ** 0.5 if scores else 0}

def run() -> None:
    print("Cross Validator test")
    e = CrossValidator(seed=42)
    data = list(range(10))
    labels = [i * 2 for i in range(10)]
    def train(x, y): return {"w": 2}
    def eval(model, x, y): return 1.0
    scores = e.k_fold(data, labels, 3, train, eval)
    print("  K-fold scores: " + str(scores))
    print("  Stats: " + str(e.get_stats(scores)))
    print("Cross Validator test complete.")

if __name__ == "__main__":
    run()
