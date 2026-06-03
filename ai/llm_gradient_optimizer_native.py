"""Gradient Optimizer - SGD, Adam, RMSprop for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum, auto
import math

class OptimizerType(Enum):
    SGD = auto()
    MOMENTUM = auto()
    ADAM = auto()
    RMSPROP = auto()
    ADAGRAD = auto()

@dataclass
class GradientOptimizer:
    optimizer_type: OptimizerType = OptimizerType.SGD
    learning_rate: float = 0.01
    beta1: float = 0.9
    beta2: float = 0.999
    epsilon: float = 1e-8
    momentum: float = 0.0
    momentum_buffer: List[List[float]] = field(default_factory=list)
    first_moment: List[List[float]] = field(default_factory=list)
    second_moment: List[List[float]] = field(default_factory=list)
    timestep: int = 0

    def step(self, weights: List[List[float]], gradients: List[List[float]]) -> List[List[float]]:
        self.timestep += 1
        t = self.timestep
        if self.optimizer_type == OptimizerType.SGD:
            return [[w - self.learning_rate * g for w, g in zip(row_w, row_g)] for row_w, row_g in zip(weights, gradients)]
        if self.optimizer_type == OptimizerType.MOMENTUM:
            if not self.momentum_buffer:
                self.momentum_buffer = [[0.0]*len(row) for row in weights]
            self.momentum_buffer = [[self.momentum * m + g for m, g in zip(row_m, row_g)] for row_m, row_g in zip(self.momentum_buffer, gradients)]
            return [[w - self.learning_rate * m for w, m in zip(row_w, row_m)] for row_w, row_m in zip(weights, self.momentum_buffer)]
        if self.optimizer_type == OptimizerType.ADAM:
            if not self.first_moment:
                self.first_moment = [[0.0]*len(row) for row in weights]
                self.second_moment = [[0.0]*len(row) for row in weights]
            self.first_moment = [[self.beta1 * m + (1-self.beta1)*g for m, g in zip(row_m, row_g)] for row_m, row_g in zip(self.first_moment, gradients)]
            self.second_moment = [[self.beta2 * v + (1-self.beta2)*g**2 for v, g in zip(row_v, row_g)] for row_v, row_g in zip(self.second_moment, gradients)]
            m_hat = [[m / (1 - self.beta1**t) for m in row] for row in self.first_moment]
            v_hat = [[v / (1 - self.beta2**t) for v in row] for row in self.second_moment]
            return [[w - self.learning_rate * m / (math.sqrt(v) + self.epsilon) for w, m, v in zip(row_w, row_m, row_v)] for row_w, row_m, row_v in zip(weights, m_hat, v_hat)]
        if self.optimizer_type == OptimizerType.RMSPROP:
            if not self.second_moment:
                self.second_moment = [[0.0]*len(row) for row in weights]
            self.second_moment = [[self.beta2 * v + (1-self.beta2)*g**2 for v, g in zip(row_v, row_g)] for row_v, row_g in zip(self.second_moment, gradients)]
            return [[w - self.learning_rate * g / (math.sqrt(v) + self.epsilon) for w, g, v in zip(row_w, row_g, row_v)] for row_w, row_g, row_v in zip(weights, gradients, self.second_moment)]
        return weights

    def stats(self) -> dict:
        return {"optimizer": self.optimizer_type.name, "lr": self.learning_rate, "steps": self.timestep}

def run():
    for opt in [OptimizerType.SGD, OptimizerType.ADAM, OptimizerType.RMSPROP]:
        optimizer = GradientOptimizer(opt, 0.01)
        weights = [[0.5, 0.3], [0.2, 0.8]]
        grads = [[0.1, 0.05], [0.02, 0.15]]
        new_w = optimizer.step(weights, grads)
        print(f"{opt.name}: new weights = {[[round(w, 4) for w in row] for row in new_w]}, stats = {optimizer.stats()}")

if __name__ == "__main__":
    run()
