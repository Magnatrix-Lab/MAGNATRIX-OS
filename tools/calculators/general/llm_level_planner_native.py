"""Level Planner — difficulty curve, pacing, encounter balance, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class LevelPlanner:
    level_id: int = 1
    encounters: List[Dict] = field(default_factory=list)
    player_power: float = 10.0

    def difficulty_score(self) -> float:
        if not self.encounters:
            return 0.0
        return sum(e.get("enemy_power", 0) for e in self.encounters) / self.player_power if self.player_power > 0 else 0.0

    def pacing(self) -> float:
        if len(self.encounters) < 2:
            return 0.0
        return len(self.encounters) / max(1.0, sum(e.get("duration_min", 1) for e in self.encounters))

    def recommended_loot(self) -> float:
        return self.difficulty_score() * self.player_power * 0.2

    def stats(self) -> Dict:
        return {"difficulty": round(self.difficulty_score(), 2), "pacing": round(self.pacing(), 3), "loot_value": round(self.recommended_loot(), 2)}

def run():
    lp = LevelPlanner(level_id=3, encounters=[{"enemy_power": 8, "duration_min": 2}, {"enemy_power": 12, "duration_min": 3}], player_power=15)
    print(lp.stats())

if __name__ == "__main__":
    run()
