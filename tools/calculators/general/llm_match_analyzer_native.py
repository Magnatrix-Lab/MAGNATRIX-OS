"""Match Analyzer — team stats, possession, xG, momentum, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class MatchAnalyzer:
    team_a_goals: int = 0
    team_b_goals: int = 0
    team_a_shots: int = 0
    team_b_shots: int = 0
    team_a_possession: float = 50.0

    def xg(self, shots: List[float]) -> float:
        return sum(shots)

    def possession_balance(self) -> str:
        if self.team_a_possession > 60:
            return "dominant A"
        elif self.team_a_possession < 40:
            return "dominant B"
        return "balanced"

    def momentum(self, events: List[int]) -> float:
        """+1 for A, -1 for B"""
        if not events:
            return 0.0
        recent = events[-10:]
        return sum(recent) / len(recent)

    def shot_efficiency(self, goals: int, shots: int) -> float:
        return goals / shots if shots > 0 else 0.0

    def stats(self) -> Dict:
        return {"score": f"{self.team_a_goals}-{self.team_b_goals}", "possession": self.possession_balance(), "eff_A": round(self.shot_efficiency(self.team_a_goals, self.team_a_shots), 3)}

def run():
    ma = MatchAnalyzer(2, 1, 10, 5, 55)
    print(ma.stats())
    print("Momentum:", ma.momentum([1,0,1,-1,1,0,0,1,0,0]))

if __name__ == "__main__":
    run()
