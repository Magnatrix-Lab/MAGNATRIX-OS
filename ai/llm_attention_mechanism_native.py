"""Attention Mechanism - Self-attention for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto
import random
import math

class AttentionType(Enum):
    SELF = auto()
    CROSS = auto()
    MULTI_HEAD = auto()

@dataclass
class AttentionMechanism:
    dim: int = 4
    attention_type: AttentionType = AttentionType.SELF
    Wq: List[List[float]] = field(default_factory=list)
    Wk: List[List[float]] = field(default_factory=list)
    Wv: List[List[float]] = field(default_factory=list)

    def __post_init__(self):
        if not self.Wq:
            scale = 0.01
            self.Wq = [[random.gauss(0, scale) for _ in range(self.dim)] for _ in range(self.dim)]
            self.Wk = [[random.gauss(0, scale) for _ in range(self.dim)] for _ in range(self.dim)]
            self.Wv = [[random.gauss(0, scale) for _ in range(self.dim)] for _ in range(self.dim)]

    def matvec(self, W: List[List[float]], x: List[float]) -> List[float]:
        return [sum(W[i][j] * x[j] for j in range(len(x))) for i in range(len(W))]

    def dot(self, a: List[float], b: List[float]) -> float:
        return sum(x*y for x, y in zip(a, b))

    def softmax(self, x: List[float]) -> List[float]:
        m = max(x)
        exps = [math.exp(v - m) for v in x]
        s = sum(exps)
        return [v/s for v in exps]

    def attention(self, query: List[float], keys: List[List[float]], values: List[List[float]]) -> List[float]:
        scores = [self.dot(query, k) / math.sqrt(self.dim) for k in keys]
        weights = self.softmax(scores)
        output = [sum(weights[i] * values[i][j] for i in range(len(values))) for j in range(self.dim)]
        return output

    def forward(self, inputs: List[List[float]]) -> List[List[float]]:
        Q = [self.matvec(self.Wq, x) for x in inputs]
        K = [self.matvec(self.Wk, x) for x in inputs]
        V = [self.matvec(self.Wv, x) for x in inputs]
        return [self.attention(q, K, V) for q in Q]

    def stats(self) -> dict:
        params = 3 * self.dim * self.dim
        return {"type": self.attention_type.name, "dim": self.dim, "params": params}

def run():
    attn = AttentionMechanism(4, AttentionType.SELF)
    inputs = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]]
    out = attn.forward(inputs)
    print("Attention output:", [[round(v, 4) for v in s] for s in out])
    print("Stats:", attn.stats())

if __name__ == "__main__":
    run()
