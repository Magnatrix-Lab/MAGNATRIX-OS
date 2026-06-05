"""Truffle Formulator — ganache ratio, shelf life, coating, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class TruffleFormulator:
    chocolate_pct: float = 50.0
    cream_pct: float = 50.0
    butter_pct: float = 0.0
    flavoring_pct: float = 0.0

    def ganache_ratio(self) -> float:
        return self.chocolate_pct / self.cream_pct if self.cream_pct > 0 else 0.0

    def texture(self) -> str:
        r = self.ganache_ratio()
        if r < 1: return "soft, pipeable"
        elif r < 1.5: return "medium, scoopable"
        elif r < 2.5: return "firm, rollable"
        return "hard, cuttable"

    def shelf_life_days(self) -> int:
        base = 14
        if self.butter_pct > 10:
            base += 7
        if self.cream_pct > 60:
            base -= 3
        return base

    def yield_count(self, size_g: float = 15) -> int:
        total = 100
        return int(total / size_g)

    def stats(self) -> Dict:
        return {"ratio": round(self.ganache_ratio(), 2), "texture": self.texture(), "shelf_life": self.shelf_life_days(), "yield": self.yield_count()}

def run():
    tf = TruffleFormulator(chocolate_pct=60, cream_pct=30, butter_pct=10)
    print(tf.stats())

if __name__ == "__main__":
    run()
