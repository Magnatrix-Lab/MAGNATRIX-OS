"""Backpropagation Engine - Gradient computation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto
import math

class LossType(Enum):
    MSE = auto()
    MAE = auto()
    CROSS_ENTROPY = auto()

@dataclass
class BackpropagationEngine:
    loss_type: LossType = LossType.MSE
    learning_rate: float = 0.01

    def compute_loss(self, predicted: List[float], target: List[float]) -> float:
        if self.loss_type == LossType.MSE:
            return sum((p - t)**2 for p, t in zip(predicted, target)) / len(predicted)
        if self.loss_type == LossType.MAE:
            return sum(abs(p - t) for p, t in zip(predicted, target)) / len(predicted)
        if self.loss_type == LossType.CROSS_ENTROPY:
            eps = 1e-10
            return -sum(t * math.log(p + eps) for p, t in zip(predicted, target)) / len(predicted)
        return 0.0

    def compute_gradients(self, weights: List[List[float]], inputs: List[float], predicted: List[float], target: List[float]) -> List[List[float]]:
        grads = []
        for i in range(len(predicted)):
            error = predicted[i] - target[i]
            grad_row = [error * inp * self.learning_rate for inp in inputs]
            grads.append(grad_row)
        return grads

    def update_weights(self, weights: List[List[float]], gradients: List[List[float]]) -> List[List[float]]:
        return [[w - g for w, g in zip(row_w, row_g)] for row_w, row_g in zip(weights, gradients)]

    def stats(self, predicted: List[float], target: List[float]) -> dict:
        loss = self.compute_loss(predicted, target)
        return {"loss_type": self.loss_type.name, "loss": round(loss, 6), "learning_rate": self.learning_rate}

def run():
    engine = BackpropagationEngine(LossType.MSE, 0.01)
    weights = [[0.1, 0.2], [0.3, 0.4]]
    inputs = [1.0, 0.5]
    predicted = [0.15, 0.35]
    target = [1.0, 0.0]
    grads = engine.compute_gradients(weights, inputs, predicted, target)
    new_weights = engine.update_weights(weights, grads)
    print("Gradients:", [[round(g, 6) for g in row] for row in grads])
    print("New weights:", [[round(w, 6) for w in row] for row in new_weights])
    print("Stats:", engine.stats(predicted, target))

if __name__ == "__main__":
    run()
