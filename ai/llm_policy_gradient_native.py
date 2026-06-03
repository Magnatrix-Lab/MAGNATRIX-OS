"""Policy Gradient - REINFORCE-style policy gradient for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
import random
import math

@dataclass
class PolicyGradient:
    num_states: int = 3; num_actions: int = 2; lr: float = 0.01
    theta: List[List[float]] = field(default_factory=list)

    def __post_init__(self):
        if not self.theta:
            self.theta = [[0.0]*self.num_actions for _ in range(self.num_states)]

    def softmax(self, x: List[float]) -> List[float]:
        m = max(x); exps = [math.exp(v-m) for v in x]; s = sum(exps)
        return [v/s for v in exps]

    def get_action(self, state: int) -> int:
        probs = self.softmax(self.theta[state])
        r = random.random(); cum = 0
        for i, p in enumerate(probs):
            cum += p
            if r < cum: return i
        return len(probs)-1

    def update(self, state: int, action: int, reward: float) -> None:
        probs = self.softmax(self.theta[state])
        for a in range(self.num_actions):
            indicator = 1 if a == action else 0
            self.theta[state][a] += self.lr * reward * (indicator - probs[a])

    def stats(self) -> dict:
        return {"states": self.num_states, "actions": self.num_actions, "lr": self.lr}

def run():
    pg = PolicyGradient(3, 2, 0.1)
    for s in range(3):
        a = pg.get_action(s)
        pg.update(s, a, 1.0)
    print("Stats:", pg.stats())

if __name__ == "__main__": run()
