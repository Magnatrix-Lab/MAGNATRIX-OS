"""Environment Simulator - Simple grid world for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
import random

class Action(Enum):
    UP = 0; DOWN = 1; LEFT = 2; RIGHT = 3

@dataclass
class EnvironmentSimulator:
    width: int = 5; height: int = 5
    agent_pos: Tuple[int,int] = (0,0)
    goal_pos: Tuple[int,int] = (4,4)
    obstacles: List[Tuple[int,int]] = field(default_factory=list)

    def reset(self) -> Tuple[int,int]:
        self.agent_pos = (0,0)
        return self.agent_pos

    def step(self, action: int) -> Tuple[Tuple[int,int], float, bool]:
        x, y = self.agent_pos
        if action == 0: x -= 1
        elif action == 1: x += 1
        elif action == 2: y -= 1
        elif action == 3: y += 1
        x = max(0, min(self.height-1, x))
        y = max(0, min(self.width-1, y))
        if (x,y) in self.obstacles:
            x, y = self.agent_pos
        self.agent_pos = (x,y)
        reward = 1.0 if self.agent_pos == self.goal_pos else -0.01
        done = self.agent_pos == self.goal_pos
        return self.agent_pos, reward, done

    def stats(self) -> dict:
        return {"size": f"{self.height}x{self.width}", "agent": self.agent_pos, "goal": self.goal_pos}

def run():
    env = EnvironmentSimulator(3, 3)
    env.goal_pos = (2,2)
    print("Reset:", env.reset())
    for a in [1,3,1,3]:
        pos, r, done = env.step(a)
        print(f"Action {a}: pos={pos}, reward={r}, done={done}")
    print("Stats:", env.stats())

if __name__ == "__main__": run()
