"""Cross-Validator — k-fold, stratified, time-series split, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Tuple
from enum import Enum, auto
import random
import math

class CVStrategy(Enum):
    K_FOLD = auto()
    STRATIFIED = auto()
    TIME_SERIES = auto()
    LEAVE_ONE_OUT = auto()

@dataclass
class CVSplit:
    fold: int
    train_indices: List[int]
    test_indices: List[int]

class CrossValidator:
    def __init__(self, strategy: CVStrategy = CVStrategy.K_FOLD, k: int = 5):
        self.strategy = strategy
        self.k = k
        self.splits: List[CVSplit] = []
        self.results: List[float] = []

    def split(self, data: List[Any], labels: Optional[List[Any]] = None) -> List[CVSplit]:
        n = len(data)
        indices = list(range(n))
        if self.strategy == CVStrategy.K_FOLD:
            fold_size = n // self.k
            for i in range(self.k):
                test = indices[i * fold_size:(i + 1) * fold_size]
                train = indices[:i * fold_size] + indices[(i + 1) * fold_size:]
                self.splits.append(CVSplit(i, train, test))
        elif self.strategy == CVStrategy.TIME_SERIES:
            for i in range(1, self.k + 1):
                split_point = int(n * i / self.k)
                train = indices[:split_point]
                test = indices[split_point:split_point + max(1, n // self.k)]
                self.splits.append(CVSplit(i - 1, train, test))
        elif self.strategy == CVStrategy.LEAVE_ONE_OUT:
            for i in range(n):
                test = [i]
                train = indices[:i] + indices[i+1:]
                self.splits.append(CVSplit(i, train, test))
        elif self.strategy == CVStrategy.STRATIFIED and labels:
            groups = {}
            for i, lbl in enumerate(labels):
                groups.setdefault(lbl, []).append(i)
            self.splits = []
            for fold in range(self.k):
                train = []
                test = []
                for lbl, grp in groups.items():
                    fold_size = len(grp) // self.k
                    test.extend(grp[fold * fold_size:(fold + 1) * fold_size])
                    train.extend(grp[:fold * fold_size] + grp[(fold + 1) * fold_size:])
                self.splits.append(CVSplit(fold, train, test))
        return self.splits

    def evaluate(self, model_fn: Callable[[List[Any], List[Any]], float], data: List[Any]) -> Dict:
        scores = []
        for split in self.splits:
            train_data = [data[i] for i in split.train_indices]
            test_data = [data[i] for i in split.test_indices]
            try:
                score = model_fn(train_data, test_data)
                scores.append(score)
            except:
                pass
        self.results = scores
        return {"mean": sum(scores) / len(scores) if scores else 0, "std": math.sqrt(sum((s - sum(scores)/len(scores))**2 for s in scores)/len(scores)) if scores else 0, "scores": scores}

    def stats(self) -> Dict:
        return {"strategy": self.strategy.name, "k": self.k, "splits": len(self.splits), "results": len(self.results)}

def run():
    cv = CrossValidator(CVStrategy.K_FOLD, 5)
    data = list(range(20))
    cv.split(data)
    def model_fn(train, test):
        return len(train) / (len(train) + len(test))
    print(cv.evaluate(model_fn, data))
    print(cv.stats())

if __name__ == "__main__":
    run()
