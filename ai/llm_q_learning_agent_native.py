"""Q-Learning Agent - RL Q-learning for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import random

@dataclass
class QLearningAgent:
    actions: List[int] = field(default_factory=list)
    alpha: float = 0.1; gamma: float = 0.9; epsilon: float = 0.1
    q_table: Dict[Tuple[int,int], float] = field(default_factory=dict)

    def choose_action(self, state: int) -> int:
        if random.random() < self.epsilon:
            return random.choice(self.actions)
        q_values = {a: self.q_table.get((state,a), 0) for a in self.actions}
        return max(q_values, key=q_values.get)

    def update(self, state: int, action: int, reward: float, next_state: int) -> None:
        q_sa = self.q_table.get((state,action), 0)
        max_q = max(self.q_table.get((next_state,a), 0) for a in self.actions) if self.actions else 0
        self.q_table[(state,action)] = q_sa + self.alpha * (reward + self.gamma * max_q - q_sa)

    def stats(self) -> dict:
        return {"actions": len(self.actions), "q_entries": len(self.q_table), "epsilon": self.epsilon}

def run():
    agent = QLearningAgent([0,1], 0.1, 0.9, 0.1)
    for _ in range(100):
        s = random.randint(0,2); a = agent.choose_action(s)
        agent.update(s, a, random.random(), random.randint(0,2))
    print("Stats:", agent.stats())

if __name__ == "__main__": run()
