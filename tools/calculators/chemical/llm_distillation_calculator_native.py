"""Distillation Calculator — ABV, proof, cuts, fraction, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class DistillationCalculator:
    wash_volume: float = 100.0
    wash_abv: float = 0.08
    still_efficiency: float = 0.85

    def total_alcohol(self) -> float:
        return self.wash_volume * self.wash_abv

    def expected_heart(self) -> float:
        return self.total_alcohol() * self.still_efficiency / 0.6

    def foreshots_pct(self) -> float:
        return 0.02

    def heads_pct(self) -> float:
        return 0.15

    def tails_pct(self) -> float:
        return 0.2

    def hearts_pct(self) -> float:
        return 1 - self.foreshots_pct() - self.heads_pct() - self.tails_pct()

    def hearts_volume(self) -> float:
        return self.expected_heart() * self.hearts_pct()

    def proof(self, abv: float) -> float:
        return abv * 2

    def stats(self) -> Dict:
        return {"total_alcohol": round(self.total_alcohol(), 1), "hearts": round(self.hearts_volume(), 1), "hearts_pct": round(self.hearts_pct(), 2)}

def run():
    dc = DistillationCalculator(wash_volume=200, wash_abv=0.1, still_efficiency=0.9)
    print(dc.stats())
    print("Proof at 60%:", dc.proof(0.6))

if __name__ == "__main__":
    run()
