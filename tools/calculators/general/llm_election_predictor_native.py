"""Election Predictor — polling, swing, electoral, coalition, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ElectionPredictor:
    parties: Dict[str, float] = field(default_factory=dict)
    """party -> poll percentage"""
    seats: Dict[str, int] = field(default_factory=dict)
    """district -> current winning party"""

    def total_poll(self) -> float:
        return sum(self.parties.values())

    def normalized(self) -> Dict[str, float]:
        total = self.total_poll()
        return {p: v / total for p, v in self.parties.items()} if total > 0 else self.parties

    def seat_projection(self) -> Dict[str, int]:
        norm = self.normalized()
        total_seats = len(self.seats)
        return {p: int(norm.get(p, 0) * total_seats) for p in norm}

    def swing_to_seats(self, swing_pct: float, from_party: str, to_party: str) -> Dict[str, int]:
        new_polls = dict(self.parties)
        new_polls[from_party] = new_polls.get(from_party, 0) - swing_pct
        new_polls[to_party] = new_polls.get(to_party, 0) + swing_pct
        total = sum(new_polls.values())
        norm = {p: v / total for p, v in new_polls.items()} if total > 0 else new_polls
        total_seats = len(self.seats)
        return {p: int(norm.get(p, 0) * total_seats) for p in norm}

    def coalition_majority(self, coalition: List[str]) -> bool:
        proj = self.seat_projection()
        total = sum(proj.get(p, 0) for p in coalition)
        return total > len(self.seats) / 2

    def stats(self) -> Dict:
        return {"parties": len(self.parties), "seats": len(self.seats), "projected": self.seat_projection()}

def run():
    ep = ElectionPredictor({"A": 42, "B": 35, "C": 15, "D": 8})
    ep.seats = {f"D{i}": "A" for i in range(50)}
    print(ep.stats())
    print("Swing 5% A->B:", ep.swing_to_seats(5, "A", "B"))
    print("Coalition A+C majority:", ep.coalition_majority(["A", "C"]))

if __name__ == "__main__":
    run()
