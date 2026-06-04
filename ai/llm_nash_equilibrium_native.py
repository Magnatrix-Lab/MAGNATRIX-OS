"""Nash Equilibrium - Game theory solver for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
from enum import Enum, auto

class GameType(Enum):
    ZERO_SUM = auto(); COORDINATION = auto()

@dataclass
class NashEquilibrium:
    payoff_matrix: List[List[Tuple[float, float]]] = field(default_factory=list)
    game_type: GameType = GameType.ZERO_SUM

    def find_pure_strategy(self) -> List[Tuple[int, int]]:
        equilibria = []
        rows = len(self.payoff_matrix)
        cols = len(self.payoff_matrix[0]) if rows > 0 else 0
        for r in range(rows):
            for c in range(cols):
                p1_payoff, p2_payoff = self.payoff_matrix[r][c]
                p1_best = max(self.payoff_matrix[i][c][0] for i in range(rows))
                p2_best = max(self.payoff_matrix[r][j][1] for j in range(cols))
                if p1_payoff == p1_best and p2_payoff == p2_best:
                    equilibria.append((r, c))
        return equilibria

    def stats(self) -> dict:
        eq = self.find_pure_strategy()
        return {"game_type": self.game_type.name, "equilibria": eq, "matrix_size": f"{len(self.payoff_matrix)}x{len(self.payoff_matrix[0]) if self.payoff_matrix else 0}"}

def run():
    ne = NashEquilibrium()
    ne.payoff_matrix = [[(-1, -1), (-3, 0)], [(0, -3), (-2, -2)]]
    print("Equilibria:", ne.find_pure_strategy())
    print("Stats:", ne.stats())

if __name__ == "__main__": run()
