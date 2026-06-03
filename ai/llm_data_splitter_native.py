"""LLM Data Splitter — Native Python (stdlib only)."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class DataSplitter:
    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    def train_test_split(self, data: List[Any], test_size: float = 0.2) -> tuple:
        shuffled = list(data)
        self._rng.shuffle(shuffled)
        split_idx = int(len(shuffled) * (1 - test_size))
        return (shuffled[:split_idx], shuffled[split_idx:])

    def k_fold(self, data: List[Any], k: int = 5) -> List[tuple]:
        shuffled = list(data)
        self._rng.shuffle(shuffled)
        fold_size = len(shuffled) // k
        folds = [shuffled[i * fold_size:(i + 1) * fold_size] for i in range(k - 1)]
        folds.append(shuffled[(k - 1) * fold_size:])
        splits = []
        for i in range(k):
            test = folds[i]
            train = [x for j, fold in enumerate(folds) for x in fold if j != i]
            splits.append((train, test))
        return splits

    def stratified_split(self, data: List[Any], labels: List[Any], test_size: float = 0.2) -> tuple:
        groups = {}
        for x, y in zip(data, labels):
            if y not in groups:
                groups[y] = []
            groups[y].append(x)
        train, test = [], []
        for label, items in groups.items():
            split_idx = int(len(items) * (1 - test_size))
            self._rng.shuffle(items)
            train.extend(items[:split_idx])
            test.extend(items[split_idx:])
        return (train, test)

    def get_stats(self, train: List[Any], test: List[Any]) -> Dict[str, Any]:
        return {"train": len(train), "test": len(test), "total": len(train) + len(test)}

def run() -> None:
    print("Data Splitter test")
    e = DataSplitter(seed=42)
    data = list(range(100))
    train, test = e.train_test_split(data, 0.2)
    print("  Train: " + str(len(train)) + ", Test: " + str(len(test)))
    folds = e.k_fold(data, 5)
    print("  K-fold: " + str(len(folds)) + " folds")
    print("  Stats: " + str(e.get_stats(train, test)))
    print("Data Splitter test complete.")

if __name__ == "__main__":
    run()
