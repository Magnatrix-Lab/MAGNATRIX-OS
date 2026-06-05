"""Video Editor — duration, cuts, pacing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class VideoEditor:
    clips: List[Dict] = field(default_factory=list)
    transitions: int = 0

    def total_duration(self) -> float:
        return sum(c.get("duration", 0) for c in self.clips)

    def cuts_per_minute(self) -> float:
        duration = self.total_duration()
        cuts = len(self.clips) - 1 + self.transitions
        return cuts / (duration / 60.0) if duration > 0 else 0.0

    def pacing_score(self) -> float:
        cpm = self.cuts_per_minute()
        return min(1.0, cpm / 15.0) if cpm > 0 else 0.0

    def stats(self) -> Dict:
        return {"duration_s": round(self.total_duration(), 2), "cpm": round(self.cuts_per_minute(), 2), "pacing": round(self.pacing_score(), 3)}

def run():
    ve = VideoEditor(clips=[{"duration": 4.5}, {"duration": 3.2}, {"duration": 5.0}], transitions=2)
    print(ve.stats())

if __name__ == "__main__":
    run()
