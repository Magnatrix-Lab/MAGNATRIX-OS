"""Choreographer — formations, counts, spacing, timing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class Choreographer:
    dancers: int = 8
    stage_width_m: float = 12.0
    stage_depth_m: float = 8.0
    counts: int = 32

    def spacing_m(self) -> float:
        return math.sqrt(self.stage_width_m * self.stage_depth_m / self.dancers) if self.dancers > 0 else 0.0

    def formation_grid(self) -> Dict:
        cols = math.ceil(math.sqrt(self.dancers))
        rows = math.ceil(self.dancers / cols)
        return {"cols": cols, "rows": rows, "dancer_width_m": round(self.stage_width_m / cols, 2), "dancer_depth_m": round(self.stage_depth_m / rows, 2)}

    def beats_total(self, bpm: float = 120.0) -> float:
        return (self.counts / bpm) * 60.0 if bpm > 0 else 0.0

    def stats(self) -> Dict:
        return {"spacing_m": round(self.spacing_m(), 2), "formation": self.formation_grid(), "duration_s": round(self.beats_total(), 2)}

def run():
    ch = Choreographer(dancers=16, stage_width_m=16, stage_depth_m=12, counts=64)
    print(ch.stats())

if __name__ == "__main__":
    run()
