"""Recurrent Layer - RNN for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto
import random
import math

class RNNType(Enum):
    VANILLA = auto()
    BIDIRECTIONAL = auto()

@dataclass
class RecurrentLayer:
    input_size: int = 4
    hidden_size: int = 3
    rnn_type: RNNType = RNNType.VANILLA
    Wxh: List[List[float]] = field(default_factory=list)
    Whh: List[List[float]] = field(default_factory=list)
    bh: List[float] = field(default_factory=list)

    def __post_init__(self):
        if not self.Wxh:
            scale = 0.01
            self.Wxh = [[random.gauss(0, scale) for _ in range(self.input_size)] for _ in range(self.hidden_size)]
            self.Whh = [[random.gauss(0, scale) for _ in range(self.hidden_size)] for _ in range(self.hidden_size)]
            self.bh = [0.0] * self.hidden_size

    def tanh(self, x: List[float]) -> List[float]:
        return [math.tanh(v) for v in x]

    def step(self, x: List[float], h_prev: List[float]) -> List[float]:
        z = [sum(x[j] * self.Wxh[i][j] for j in range(self.input_size)) + sum(h_prev[k] * self.Whh[i][k] for k in range(self.hidden_size)) + self.bh[i] for i in range(self.hidden_size)]
        return self.tanh(z)

    def forward(self, sequence: List[List[float]]) -> List[List[float]]:
        h = [0.0] * self.hidden_size
        states = []
        for x in sequence:
            h = self.step(x, h)
            states.append(h)
        return states

    def stats(self) -> dict:
        return {"rnn_type": self.rnn_type.name, "input": self.input_size, "hidden": self.hidden_size, "params": self.input_size * self.hidden_size + self.hidden_size * self.hidden_size + self.hidden_size}

def run():
    rnn = RecurrentLayer(3, 2, RNNType.VANILLA)
    seq = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    states = rnn.forward(seq)
    print("Hidden states:", [[round(v, 4) for v in s] for s in states])
    print("Stats:", rnn.stats())

if __name__ == "__main__":
    run()
