"""Game Mechanics — probability, balancing, progression, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import random

@dataclass
class GameMechanics:
    player_level: int = 1
    xp_per_level: List[int] = field(default_factory=lambda: [100, 200, 400, 800, 1600])
    difficulty_scale: float = 1.2

    def xp_to_next(self) -> int:
        if self.player_level - 1 < len(self.xp_per_level):
            return self.xp_per_level[self.player_level - 1]
        return int(self.xp_per_level[-1] * (self.difficulty_scale ** (self.player_level - len(self.xp_per_level))))

    def total_xp_to_level(self, target: int) -> int:
        return sum(self.xp_per_level[i] if i < len(self.xp_per_level) else self.xp_per_level[-1] * int(self.difficulty_scale ** (i - len(self.xp_per_level) + 1)) for i in range(target - 1))

    def loot_probability(self, rarity: str, luck_bonus: float = 0) -> float:
        base = {"common": 0.5, "uncommon": 0.3, "rare": 0.15, "epic": 0.05, "legendary": 0.01}
        return min(1.0, base.get(rarity, 0.1) + luck_bonus)

    def roll_loot(self, luck_bonus: float = 0) -> str:
        r = random.random()
        cumulative = 0
        for rarity, prob in [("common", 0.5), ("uncommon", 0.3), ("rare", 0.15), ("epic", 0.05), ("legendary", 0.01)]:
            cumulative += prob + luck_bonus
            if r < cumulative:
                return rarity
        return "common"

    def stats(self) -> Dict:
        return {"level": self.player_level, "xp_next": self.xp_to_next(), "total_to_10": self.total_xp_to_level(10)}

def run():
    gm = GameMechanics(player_level=3)
    print(gm.stats())
    print("Loot rolls:", [gm.roll_loot() for _ in range(5)])

if __name__ == "__main__":
    run()
