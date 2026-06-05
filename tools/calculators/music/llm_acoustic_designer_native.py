"""Acoustic Designer — RT60, absorption, STC, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class AcousticDesigner:
    room_volume_m3: float = 100.0
    total_absorption: float = 15.0
    distance_m: float = 3.0

    def rt60(self) -> float:
        return 0.161 * self.room_volume_m3 / self.total_absorption if self.total_absorption > 0 else 0.0

    def spl_drop(self, source_spl: float = 85.0) -> float:
        return source_spl - 20 * math.log10(self.distance_m) if self.distance_m > 0 else source_spl

    def recommended_absorption(self) -> float:
        return 0.161 * self.room_volume_m3 / 0.5

    def stats(self) -> Dict:
        return {"rt60_s": round(self.rt60(), 2), "spl_at_listener": round(self.spl_drop(), 2), "target_absorption": round(self.recommended_absorption(), 2)}

def run():
    ad = AcousticDesigner(room_volume_m3=200, total_absorption=25, distance_m=4)
    print(ad.stats())

if __name__ == "__main__":
    run()
