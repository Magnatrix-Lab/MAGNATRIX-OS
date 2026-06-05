"""Decision Tree Builder — ID3/CART-style, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum, auto
import math

class SplitType(Enum):
    CATEGORICAL = auto()
    NUMERICAL = auto()

@dataclass
class TreeNode:
    feature: Optional[str] = None
    threshold: Optional[float] = None
    children: Dict[Any, "TreeNode"] = field(default_factory=dict)
    label: Optional[Any] = None
    split_type: Optional[SplitType] = None
    info: Dict = field(default_factory=dict)

class DecisionTree:
    def __init__(self, max_depth: int = 5, min_samples: int = 2):
        self.max_depth = max_depth
        self.min_samples = min_samples
        self.root: Optional[TreeNode] = None
        self.features: List[str] = []

    def _entropy(self, labels: List[Any]) -> float:
        counts = {}
        for l in labels:
            counts[l] = counts.get(l, 0) + 1
        total = len(labels)
        return -sum((c/total) * math.log2(c/total) for c in counts.values() if c > 0)

    def _information_gain(self, data: List[Dict], labels: List[Any], feature: str) -> float:
        base = self._entropy(labels)
        values = {}
        for d, l in zip(data, labels):
            v = d.get(feature)
            if v not in values:
                values[v] = []
            values[v].append(l)
        weighted = sum((len(v)/len(labels)) * self._entropy(v) for v in values.values())
        return base - weighted

    def _best_split(self, data: List[Dict], labels: List[Any], depth: int) -> TreeNode:
        if len(set(labels)) == 1 or len(labels) < self.min_samples or depth >= self.max_depth:
            return TreeNode(label=max(set(labels), key=labels.count))
        best_gain = -1
        best_feature = None
        for f in self.features:
            gain = self._information_gain(data, labels, f)
            if gain > best_gain:
                best_gain = gain
                best_feature = f
        if best_gain <= 0 or not best_feature:
            return TreeNode(label=max(set(labels), key=labels.count))
        node = TreeNode(feature=best_feature, split_type=SplitType.CATEGORICAL)
        values = {}
        for d, l in zip(data, labels):
            v = d.get(best_feature)
            if v not in values:
                values[v] = ([], [])
            values[v][0].append(d)
            values[v][1].append(l)
        for v, (sub_data, sub_labels) in values.items():
            node.children[v] = self._best_split(sub_data, sub_labels, depth + 1)
        return node

    def fit(self, data: List[Dict], labels: List[Any]):
        self.features = list(data[0].keys()) if data else []
        self.root = self._best_split(data, labels, 0)

    def predict(self, sample: Dict) -> Any:
        node = self.root
        while node and node.label is None:
            v = sample.get(node.feature)
            node = node.children.get(v, node.children.get(list(node.children.keys())[0]) if node.children else None)
        return node.label if node else None

    def predict_batch(self, data: List[Dict]) -> List[Any]:
        return [self.predict(d) for d in data]

    def stats(self) -> Dict:
        return {"max_depth": self.max_depth, "features": self.features, "root": self.root.feature if self.root else None}

def run():
    data = [{"color": "red", "size": "small"}, {"color": "red", "size": "big"}, {"color": "green", "size": "small"}, {"color": "green", "size": "big"}]
    labels = ["apple", "apple", "pear", "watermelon"]
    tree = DecisionTree(max_depth=3)
    tree.fit(data, labels)
    print(tree.predict({"color": "red", "size": "small"}))
    print(tree.stats())

if __name__ == "__main__":
    run()
