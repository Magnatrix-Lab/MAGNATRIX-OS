"""LSTM Cell - Long Short-Term Memory for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto
import random
import math

@dataclass
class LSTMCell:
    input_size: int = 4
    hidden_size: int = 3
    Wf: List[List[float]] = field(default_factory=list)
    Wi: List[List[float]] = field(default_factory=list)
    Wc: List[List[float]] = field(default_factory=list)
    Wo: List[List[float]] = field(default_factory=list)
    bf: List[float] = field(default_factory=list)
    bi: List[float] = field(default_factory=list)
    bc: List[float] = field(default_factory=list)
    bo: List[float] = field(default_factory=list)

    def __post_init__(self):
        if not self.Wf:
            scale = 0.01
            for attr in ['Wf', 'Wi', 'Wc', 'Wo']:
                setattr(self, attr, [[random.gauss(0, scale) for _ in range(self.input_size)] for _ in range(self.hidden_size)])
            for attr in ['bf', 'bi', 'bc', 'bo']:
                setattr(self, attr, [0.0] * self.hidden_size)

    def sigmoid(self, x: float) -> float: return 1.0 / (1.0 + math.exp(-x))
    def tanh(self, x: float) -> float: return math.tanh(x)

    def step(self, x: List[float], h_prev: List[float], c_prev: List[float]) -> Tuple[List[float], List[float]]:
        h = self.hidden_size
        f = [self.sigmoid(sum(x[j]*self.Wf[i][j] for j in range(self.input_size)) + sum(h_prev[k]*self.Wf[i][k] for k in range(h)) + self.bf[i]) for i in range(h)]
        i_gate = [self.sigmoid(sum(x[j]*self.Wi[i][j] for j in range(self.input_size)) + sum(h_prev[k]*self.Wi[i][k] for k in range(h)) + self.bi[i]) for i in range(h)]
        c_tilde = [self.tanh(sum(x[j]*self.Wc[i][j] for j in range(self.input_size)) + sum(h_prev[k]*self.Wc[i][k] for k in range(h)) + self.bc[i]) for i in range(h)]
        c = [f[idx]*c_prev[idx] + i_gate[idx]*c_tilde[idx] for idx in range(h)]
        o = [self.sigmoid(sum(x[j]*self.Wo[i][j] for j in range(self.input_size)) + sum(h_prev[k]*self.Wo[i][k] for k in range(h)) + self.bo[i]) for i in range(h)]
        h_new = [o[idx]*self.tanh(c[idx]) for idx in range(h)]
        return h_new, c

    def forward(self, sequence: List[List[float]]) -> List[List[float]]:
        h, c = [0.0]*self.hidden_size, [0.0]*self.hidden_size
        states = []
        for x in sequence:
            h, c = self.step(x, h, c)
            states.append(h)
        return states

    def stats(self) -> dict:
        params = 4 * (self.input_size * self.hidden_size + self.hidden_size * self.hidden_size + self.hidden_size)
        return {"input": self.input_size, "hidden": self.hidden_size, "params": params}

def run():
    lstm = LSTMCell(3, 2)
    seq = [[0.2, 0.4, 0.6], [0.1, 0.3, 0.5], [0.7, 0.2, 0.1]]
    out = lstm.forward(seq)
    print("LSTM output:", [[round(v, 4) for v in s] for s in out])
    print("Stats:", lstm.stats())

if __name__ == "__main__":
    run()
