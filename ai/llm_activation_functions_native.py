"""Activation Functions - Deep learning activation primitives for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Callable, Optional
from enum import Enum, auto
import math

class ActivationName(Enum):
    RELU = auto()
    LEAKY_RELU = auto()
    ELU = auto()
    GELU = auto()
    SWISH = auto()
    MISH = auto()
    SELU = auto()
    HARD_SIGMOID = auto()
    SOFTPLUS = auto()

@dataclass
class ActivationFunction:
    name: ActivationName
    alpha: float = 0.01

    def apply(self, x: float) -> float:
        n = self.name
        if n == ActivationName.RELU: return max(0.0, x)
        if n == ActivationName.LEAKY_RELU: return x if x > 0 else self.alpha * x
        if n == ActivationName.ELU: return x if x > 0 else self.alpha * (math.exp(x) - 1)
        if n == ActivationName.GELU: return 0.5 * x * (1 + math.tanh(math.sqrt(2 / math.pi) * (x + 0.044715 * x**3)))
        if n == ActivationName.SWISH: return x / (1 + math.exp(-x))
        if n == ActivationName.MISH: return x * math.tanh(math.log(1 + math.exp(x)))
        if n == ActivationName.SELU: return 1.0507 * x if x > 0 else 1.7581 * (math.exp(x) - 1)
        if n == ActivationName.HARD_SIGMOID: return max(0.0, min(1.0, 0.2 * x + 0.5))
        if n == ActivationName.SOFTPLUS: return math.log(1 + math.exp(x))
        return x

    def apply_batch(self, inputs: List[float]) -> List[float]:
        return [self.apply(x) for x in inputs]

    def stats(self, inputs: List[float]) -> dict:
        out = self.apply_batch(inputs)
        return {"name": self.name.name, "inputs": len(inputs), "min_out": round(min(out), 4), "max_out": round(max(out), 4), "avg_out": round(sum(out)/len(out), 4) if out else 0}

def run():
    acts = [ActivationName.RELU, ActivationName.GELU, ActivationName.SWISH, ActivationName.MISH]
    inputs = [-2.0, -1.0, 0.0, 1.0, 2.0]
    for a in acts:
        af = ActivationFunction(a)
        print(f"{a.name}: {af.stats(inputs)}")

if __name__ == "__main__":
    run()
