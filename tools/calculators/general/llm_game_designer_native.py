"""Game Designer — mechanics, balance, progression, reward curves, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class GameDesigner:
    player_level: int = 1
    xp_to_level_base: float = 100.0
    xp_growth_rate: float = 1.5

    def xp_for_level(self, target_level: int) -> float:
        return self.xp_to_level_base * (self.xp_growth_rate ** (target_level - 1))

    def total_xp_to_level(self, target_level: int) -> float:
        return sum(self.xp_for_level(l) for l in range(1, target_level + 1))

    def reward_curve(self, difficulty: float = 1.0) -> float:
        return math.log(self.player_level + 1) * difficulty * 10.0

    def time_to_level(self, xp_per_hour: float = 50.0) -> float:
        return self.xp_for_level(self.player_level + 1) / xp_per_hour if xp_per_hour > 0 else 0.0

    def stats(self) -> Dict:
        return {"next_level_xp": round(self.xp_for_level(self.player_level + 1), 2), "ttnl_hours": round(self.time_to_level(), 2), "reward": round(self.reward_curve(), 2)}

def run():
    gd = GameDesigner(player_level=5, xp_to_level_base=100, xp_growth_rate=1.4)
    print(gd.stats())

if __name__ == "__main__":
    run()
