"""Audio Mixer — gain staging, pan, dBFS, headroom, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class AudioMixer:
    tracks: List[Dict] = field(default_factory=list)
    master_gain_db: float = 0.0

    def sum_db(self) -> float:
        if not self.tracks:
            return -float("inf")
        total_linear = sum(10 ** (t.get("gain_db", -96) / 20.0) for t in self.tracks)
        return 20 * math.log10(total_linear) if total_linear > 0 else -96.0

    def headroom(self) -> float:
        return -0.5 - (self.sum_db() + self.master_gain_db)

    def pan_position(self, pan: float = 0.0) -> Dict:
        return {"left": round((1 - pan) / 2, 3), "right": round((1 + pan) / 2, 3)}

    def stats(self) -> Dict:
        return {"sum_db": round(self.sum_db(), 2), "headroom": round(self.headroom(), 2), "pan": self.pan_position(0.3)}

def run():
    am = AudioMixer(tracks=[{"gain_db": -12}, {"gain_db": -10}, {"gain_db": -15}], master_gain_db=-2)
    print(am.stats())

if __name__ == "__main__":
    run()
