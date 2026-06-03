"""Neural Layer - Deep learning layer primitives for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from enum import Enum, auto
import random
import math

class LayerType(Enum):
    DENSE = auto()
    CONV = auto()
    POOL = auto()
    DROPOUT = auto()
    BATCHNORM = auto()

class ActivationType(Enum):
    RELU = auto()
    SIGMOID = auto()
    TANH = auto()
    SOFTMAX = auto()
    LINEAR = auto()

@dataclass
class NeuralLayer:
    name: str
    layer_type: LayerType
    input_size: int
    output_size: int
    activation: ActivationType = ActivationType.LINEAR
    weights: List[List[float]] = field(default_factory=list)
    biases: List[float] = field(default_factory=list)
    dropout_rate: float = 0.0

    def __post_init__(self):
        if not self.weights:
            scale = math.sqrt(2.0 / self.input_size) if self.activation == ActivationType.RELU else math.sqrt(1.0 / self.input_size)
            self.weights = [[random.gauss(0, scale) for _ in range(self.input_size)] for _ in range(self.output_size)]
        if not self.biases:
            self.biases = [0.0] * self.output_size

    def activate(self, x: float) -> float:
        if self.activation == ActivationType.RELU: return max(0.0, x)
        if self.activation == ActivationType.SIGMOID: return 1.0 / (1.0 + math.exp(-x))
        if self.activation == ActivationType.TANH: return math.tanh(x)
        return x

    def forward(self, inputs: List[float]) -> List[float]:
        outputs = []
        for i in range(self.output_size):
            z = sum(inputs[j] * self.weights[i][j] for j in range(self.input_size)) + self.biases[i]
            outputs.append(self.activate(z))
        return outputs

    def stats(self) -> dict:
        total = sum(sum(w) for w in self.weights)
        return {"name": self.name, "type": self.layer_type.name, "weights": len(self.weights) * len(self.weights[0]), "weight_sum": round(total, 4)}

def run():
    layer = NeuralLayer("hidden1", LayerType.DENSE, 4, 3, ActivationType.RELU)
    out = layer.forward([1.0, 0.5, -0.2, 0.3])
    print("Layer output:", [round(x, 4) for x in out])
    print("Stats:", layer.stats())

if __name__ == "__main__":
    run()
