"""Rhythm Generator — beat patterns, tempo, swing, polyrhythms, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class RhythmGenerator:
    bpm: float = 120.0
    beats_per_bar: int = 4
    note_value: int = 4

    def beat_duration(self) -> float:
        return 60.0 / self.bpm

    def bar_duration(self) -> float:
        return self.beats_per_bar * self.beat_duration()

    def generate_pattern(self, hits: List[int]) -> List[Tuple[float, float]]:
        beat_dur = self.beat_duration()
        return [(i * beat_dur, beat_dur) for i, hit in enumerate(hits) if hit]

    def swing_timing(self, straight: List[float], swing_pct: float = 0.6) -> List[float]:
        result = []
        for i, t in enumerate(straight):
            if i % 2 == 1:
                result.append(t + (straight[i] - straight[i-1]) * (swing_pct - 0.5) if i > 0 else t)
            else:
                result.append(t)
        return result

    def polyrhythm(self, pulses1: int, pulses2: int, steps: int) -> List[Tuple[int, int]]:
        pattern = []
        for i in range(steps):
            hit1 = 1 if (i * pulses1) % steps < pulses1 else 0
            hit2 = 1 if (i * pulses2) % steps < pulses2 else 0
            pattern.append((hit1, hit2))
        return pattern

    def stats(self) -> Dict:
        return {"bpm": self.bpm, "beat_dur": round(self.beat_duration(), 4)}

def run():
    rg = RhythmGenerator(bpm=120)
    print("Pattern:", rg.generate_pattern([1,0,1,0,1,0,1,0]))
    print("Poly:", rg.polyrhythm(3, 4, 12))
    print(rg.stats())

if __name__ == "__main__":
    run()
