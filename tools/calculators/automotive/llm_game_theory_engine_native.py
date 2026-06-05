"""Game Theory Engine — Nash equilibrium, payoff matrices, dominant strategies, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

@dataclass
class GameTheoryEngine:
    payoffs: List[List[Tuple[float, float]]] = field(default_factory=list)
    """[row][col] = (player1_payoff, player2_payoff)"""

    def best_response(self, player: int, opponent_strategy: int) -> List[int]:
        if player == 0:
            col = opponent_strategy
            payoffs = [self.payoffs[r][col][0] for r in range(len(self.payoffs))]
        else:
            row = opponent_strategy
            payoffs = [self.payoffs[row][c][1] for c in range(len(self.payoffs[0]))]
        max_pay = max(payoffs)
        return [i for i, p in enumerate(payoffs) if p == max_pay]

    def nash_equilibrium(self) -> List[Tuple[int, int]]:
        equilibria = []
        for r in range(len(self.payoffs)):
            for c in range(len(self.payoffs[0])):
                if r in self.best_response(0, c) and c in self.best_response(1, r):
                    equilibria.append((r, c))
        return equilibria

    def dominant_strategy(self, player: int) -> Optional[int]:
        if player == 0:
            strategies = range(len(self.payoffs))
            for s in strategies:
                is_dominant = True
                for other in strategies:
                    if other == s:
                        continue
                    for c in range(len(self.payoffs[0])):
                        if self.payoffs[s][c][0] < self.payoffs[other][c][0]:
                            is_dominant = False
                            break
                    if not is_dominant:
                        break
                if is_dominant:
                    return s
        else:
            strategies = range(len(self.payoffs[0]))
            for s in strategies:
                is_dominant = True
                for other in strategies:
                    if other == s:
                        continue
                    for r in range(len(self.payoffs)):
                        if self.payoffs[r][s][1] < self.payoffs[r][other][1]:
                            is_dominant = False
                            break
                    if not is_dominant:
                        break
                if is_dominant:
                    return s
        return None

    def stats(self) -> Dict:
        return {"rows": len(self.payoffs), "cols": len(self.payoffs[0]) if self.payoffs else 0}

def run():
    gte = GameTheoryEngine([[((3,3),(0,5)),((5,0),(1,1))]])
    # Prisoner's dilemma: [[(3,3),(0,5)],[(5,0),(1,1)]]
    gte = GameTheoryEngine([[(3,3),(0,5)],[(5,0),(1,1)]])
    print("Nash:", gte.nash_equilibrium())
    print("Dominant P1:", gte.dominant_strategy(0))
    print(gte.stats())

if __name__ == "__main__":
    run()
