"""NPC Behavior Planner — FSM, patrol, aggro, AI decision weights, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class NPCBehaviorPlanner:
    sight_range_m: float = 15.0
    hearing_range_m: float = 10.0
    patrol_points: List[Dict] = field(default_factory=list)

    def aggro_trigger(self, player_distance_m: float, player_noise: float = 0.0) -> bool:
        return player_distance_m <= self.sight_range_m or (player_noise > 0.5 and player_distance_m <= self.hearing_range_m)

    def patrol_path_length(self) -> float:
        if len(self.patrol_points) < 2:
            return 0.0
        total = 0.0
        for i in range(len(self.patrol_points) - 1):
            a = self.patrol_points[i]
            b = self.patrol_points[i + 1]
            total += math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)
        return total

    def decision_weights(self) -> Dict:
        return {"attack": 0.4, "patrol": 0.3, "flee": 0.2, "idle": 0.1}

    def stats(self) -> Dict:
        return {"patrol_length_m": round(self.patrol_path_length(), 2), "aggro_5m": self.aggro_trigger(5.0), "weights": self.decision_weights()}

def run():
    npc = NPCBehaviorPlanner(sight_range_m=20, patrol_points=[{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 10}])
    print(npc.stats())

if __name__ == "__main__":
    run()
