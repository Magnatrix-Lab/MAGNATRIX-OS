"""Voting System — plurality, Borda, Condorcet, STV, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class VotingSystem:
    ballots: List[List[str]] = field(default_factory=list)
    """Each ballot: ranked list of candidates"""

    def add_ballot(self, ballot: List[str]):
        self.ballots.append(ballot)

    def plurality(self) -> Dict[str, int]:
        votes = {}
        for b in self.ballots:
            if b:
                votes[b[0]] = votes.get(b[0], 0) + 1
        return votes

    def borda(self) -> Dict[str, int]:
        scores = {}
        for b in self.ballots:
            for i, c in enumerate(b):
                scores[c] = scores.get(c, 0) + (len(b) - i - 1)
        return scores

    def condorcet_winner(self) -> Optional[str]:
        candidates = set(c for b in self.ballots for c in b)
        for c in candidates:
            wins_all = True
            for o in candidates:
                if c == o:
                    continue
                c_wins = sum(1 for b in self.ballots if b.index(c) < b.index(o) if c in b and o in b)
                o_wins = sum(1 for b in self.ballots if b.index(o) < b.index(c) if c in b and o in b)
                if c_wins <= o_wins:
                    wins_all = False
                    break
            if wins_all:
                return c
        return None

    def stv(self, seats: int = 1) -> List[str]:
        candidates = list(set(c for b in self.ballots for c in b))
        quota = len(self.ballots) // (seats + 1) + 1
        elected = []
        while len(elected) < seats and candidates:
            first_prefs = {}
            for b in self.ballots:
                for c in b:
                    if c in candidates:
                        first_prefs[c] = first_prefs.get(c, 0) + 1
                        break
            if not first_prefs:
                break
            winner = max(first_prefs, key=first_prefs.get)
            if first_prefs[winner] >= quota:
                elected.append(winner)
                candidates.remove(winner)
            else:
                loser = min(first_prefs, key=first_prefs.get)
                candidates.remove(loser)
        return elected

    def stats(self) -> Dict:
        return {"ballots": len(self.ballots), "plurality": self.plurality(), "borda": self.borda()}

def run():
    vs = VotingSystem()
    vs.add_ballot(["A", "B", "C"])
    vs.add_ballot(["A", "C", "B"])
    vs.add_ballot(["B", "A", "C"])
    vs.add_ballot(["C", "B", "A"])
    print(vs.stats())
    print("Condorcet:", vs.condorcet_winner())
    print("STV:", vs.stv(1))

if __name__ == "__main__":
    run()
