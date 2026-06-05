"""Mastering Engine — loudness, true peak, stereo width, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class MasteringEngine:
    lufs_integrated: float = -14.0
    true_peak_db: float = -1.0
    stereo_width: float = 1.0

    def loudness_range(self, lufs_max: float = -8.0) -> float:
        return lufs_max - self.lufs_integrated

    def needs_limiter(self) -> bool:
        return self.true_peak_db > -1.0

    def width_percentage(self) -> float:
        return self.stereo_width * 100.0

    def stats(self) -> Dict:
        return {"lufs": self.lufs_integrated, "true_peak": self.true_peak_db, "needs_limiter": self.needs_limiter(), "width_pct": round(self.width_percentage(), 1)}

def run():
    me = MasteringEngine(lufs_integrated=-11.0, true_peak_db=-0.5, stereo_width=0.85)
    print(me.stats())

if __name__ == "__main__":
    run()
