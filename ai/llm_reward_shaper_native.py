"""Reward Shaper - Reward shaping for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Callable
import math

@dataclass
class RewardShaper:
    goal_pos: Tuple[int,int] = (0,0)

    def distance_reward(self, pos: Tuple[int,int]) -> float:
        d = math.sqrt((pos[0]-self.goal_pos[0])**2 + (pos[1]-self.goal_pos[1])**2)
        return -d * 0.1

    def shaped_reward(self, pos: Tuple[int,int], base_reward: float) -> float:
        return base_reward + self.distance_reward(pos)

    def stats(self) -> dict:
        return {"goal": self.goal_pos}

def run():
    rs = RewardShaper((4,4))
    for pos in [(0,0),(1,1),(3,3),(4,4)]:
        print(f"Pos {pos}: shaped={round(rs.shaped_reward(pos, 0), 2)}")
    print("Stats:", rs.stats())

if __name__ == "__main__": run()
