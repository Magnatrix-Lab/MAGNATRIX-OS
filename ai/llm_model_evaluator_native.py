"""LLM Model Evaluator — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class ModelEvaluator:
    def __init__(self) -> None:
        pass

    def accuracy(self, actual: List[Any], predicted: List[Any]) -> float:
        if len(actual) != len(predicted) or not actual:
            return 0.0
        correct = sum(1 for a, p in zip(actual, predicted) if a == p)
        return correct / len(actual)

    def precision_recall_f1(self, actual: List[int], predicted: List[int], positive: int = 1) -> Dict[str, float]:
        tp = sum(1 for a, p in zip(actual, predicted) if a == positive and p == positive)
        fp = sum(1 for a, p in zip(actual, predicted) if a != positive and p == positive)
        fn = sum(1 for a, p in zip(actual, predicted) if a == positive and p != positive)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return {"precision": precision, "recall": recall, "f1": f1}

    def rmse(self, actual: List[float], predicted: List[float]) -> float:
        if len(actual) != len(predicted) or not actual:
            return 0.0
        return math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual))

    def mae(self, actual: List[float], predicted: List[float]) -> float:
        if len(actual) != len(predicted) or not actual:
            return 0.0
        return sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual)

    def get_stats(self, actual: List[Any], predicted: List[Any]) -> Dict[str, Any]:
        return {"accuracy": self.accuracy(actual, predicted), "rmse": self.rmse(actual, predicted) if isinstance(actual[0], float) else 0}

def run() -> None:
    print("Model Evaluator test")
    e = ModelEvaluator()
    actual = [1, 0, 1, 1, 0]
    predicted = [1, 0, 1, 0, 0]
    print("  Accuracy: " + str(e.accuracy(actual, predicted)))
    print("  P/R/F1: " + str(e.precision_recall_f1(actual, predicted)))
    print("  Stats: " + str(e.get_stats(actual, predicted)))
    print("Model Evaluator test complete.")

if __name__ == "__main__":
    run()
