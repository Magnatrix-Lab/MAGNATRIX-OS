"""Pastry Laminate — layers, butter ratio, folds, turns, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class PastryLaminate:
    initial_layers: int = 1
    turns: int = 3
    folds_per_turn: int = 3
    butter_dough_ratio: float = 0.5

    def total_layers(self) -> int:
        return self.initial_layers * (self.folds_per_turn ** self.turns)

    def butter_per_fold(self) -> float:
        return self.butter_dough_ratio / self.turns

    def resting_time_between_turns(self) -> int:
        return 30

    def total_resting(self) -> int:
        return self.resting_time_between_turns() * (self.turns - 1)

    def layer_thickness(self, dough_thickness_mm: float = 5) -> float:
        return dough_thickness_mm / self.total_layers()

    def butter_integrity_risk(self) -> str:
        if self.butter_dough_ratio > 0.6 and self.turns > 4:
            return "high"
        elif self.butter_dough_ratio > 0.5:
            return "moderate"
        return "low"

    def stats(self) -> Dict:
        return {"layers": self.total_layers(), "layer_thickness": round(self.layer_thickness(), 4), "total_rest": self.total_resting(), "risk": self.butter_integrity_risk()}

def run():
    pl = PastryLaminate(turns=4, folds_per_turn=3, butter_dough_ratio=0.55)
    print(pl.stats())

if __name__ == "__main__":
    run()
