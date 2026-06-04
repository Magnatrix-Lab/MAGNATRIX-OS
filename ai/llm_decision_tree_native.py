"""Decision Tree - Classification tree for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import math
from collections import Counter

@dataclass
class DTNode:
    feature: int = -1
    threshold: float = 0.0
    left: Optional["DTNode"] = None
    right: Optional["DTNode"] = None
    label: Optional[str] = None

@dataclass
class DecisionTree:
    max_depth: int = 3
    root: Optional[DTNode] = None

    def fit(self, X: List[List[float]], y: List[str]) -> None:
        self.root = self._build(X, y, 0)

    def _build(self, X, y, depth):
        if len(set(y)) == 1 or depth >= self.max_depth or not X:
            return DTNode(label=max(set(y), key=y.count) if y else None)
        best_gain = -1
        best_feature = 0
        best_threshold = 0.0
        for feature in range(len(X[0])):
            values = sorted(set(row[feature] for row in X))
            for threshold in values:
                left_y = [y[i] for i in range(len(X)) if X[i][feature] <= threshold]
                right_y = [y[i] for i in range(len(X)) if X[i][feature] > threshold]
                gain = self._information_gain(y, left_y, right_y)
                if gain > best_gain:
                    best_gain = gain
                    best_feature = feature
                    best_threshold = threshold
        left_X = [X[i] for i in range(len(X)) if X[i][best_feature] <= best_threshold]
        left_y = [y[i] for i in range(len(X)) if X[i][best_feature] <= best_threshold]
        right_X = [X[i] for i in range(len(X)) if X[i][best_feature] > best_threshold]
        right_y = [y[i] for i in range(len(X)) if X[i][best_feature] > best_threshold]
        node = DTNode(best_feature, best_threshold)
        node.left = self._build(left_X, left_y, depth + 1)
        node.right = self._build(right_X, right_y, depth + 1)
        return node

    def _entropy(self, y):
        if not y: return 0
        counts = Counter(y)
        total = len(y)
        return -sum((c/total) * math.log2(c/total) for c in counts.values() if c > 0)

    def _information_gain(self, parent, left, right):
        if not left or not right: return 0
        parent_entropy = self._entropy(parent)
        n = len(parent)
        weighted = (len(left)/n) * self._entropy(left) + (len(right)/n) * self._entropy(right)
        return parent_entropy - weighted

    def predict(self, x: List[float]) -> str:
        node = self.root
        while node and node.label is None:
            if x[node.feature] <= node.threshold: node = node.left
            else: node = node.right
        return node.label if node else ""

    def stats(self, X: List[List[float]], y: List[str]) -> dict:
        predictions = [self.predict(x) for x in X]
        accuracy = sum(1 for p, t in zip(predictions, y) if p == t) / len(y) if y else 0
        return {"accuracy": round(accuracy, 4), "depth": self.max_depth}

def run():
    dt = DecisionTree(2)
    X = [[1, 2], [2, 3], [3, 1], [4, 4], [5, 2], [6, 5]]
    y = ["A", "A", "A", "B", "B", "B"]
    dt.fit(X, y)
    print("Predict [3,2]:", dt.predict([3, 2]))
    print("Stats:", dt.stats(X, y))

if __name__ == "__main__": run()
